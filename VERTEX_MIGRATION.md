# Vertex AI Migration Plan

Goal: move our Gemini calls off `generativelanguage.googleapis.com` (the Gemini API, shared global capacity, preview-model-heavy) onto Vertex AI (per-project capacity, GA models, attachable to our GCE service account) to eliminate the frequent `503 UNAVAILABLE` errors.

**Scope of impact today** (all preview models, all on the Gemini API):

| Call site | File | Current model | Blocks user? |
|---|---|---|---|
| Live voice pipeline | `backend/app/voice/pipeline.py` | `gemini-3.1-flash-live-preview` (preview) | Yes (call fails to start) |
| Conversation monitor | `backend/app/voice/monitor.py` | `gemini-3.1-flash-lite-preview` (preview) | No (degraded silently) |
| Note verify (post add_item) | `backend/app/voice/tools.py` | `gemini-3-flash-preview` (preview) | No (degraded silently) |
| Menu image extract | `backend/app/api/routers/store/menu.py` | `gemini-3-flash-preview` (preview) | Yes (error toast) |
| Custom prompt generator | `backend/app/api/routers/store/ai.py` | `gemini-3-flash-preview` (preview) | Yes (error toast) |

Target models on Vertex (all GA, `google/` prefix is mandatory):

- Live voice → `google/gemini-live-2.5-flash-native-audio` (GA, native audio)
- Everything else → `google/gemini-2.5-flash` (GA, multimodal, fast, cheap)

---

## Phase 0 — GCP setup (one-time, no code)

**Owner: human, done in GCP Console / `gcloud` CLI.**

1. **Choose a project** — reuse the existing Rest-OAI project where the GCE VM lives (same billing account), or spin up a dedicated `restoai-prod` project. Reusing is simpler; dedicated is cleaner for cost attribution.
2. **Enable the Vertex AI API**:
   ```
   gcloud services enable aiplatform.googleapis.com --project=<PROJECT_ID>
   ```
3. **Confirm billing is active** on the project. Vertex AI has **no free tier** — every token is billed. Without billing enabled every call returns `403`.
4. **Create / pick a service account** and grant it the right role:
   ```
   gcloud iam service-accounts create restoai-vertex \
     --display-name="RestoAI Vertex client" --project=<PROJECT_ID>

   gcloud projects add-iam-policy-binding <PROJECT_ID> \
     --member="serviceAccount:restoai-vertex@<PROJECT_ID>.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```
5. **Attach the SA to the production GCE instance** so ADC works automatically (no secret files):
   ```
   gcloud compute instances set-service-account <VM_NAME> \
     --zone=<ZONE> \
     --service-account=restoai-vertex@<PROJECT_ID>.iam.gserviceaccount.com \
     --scopes=https://www.googleapis.com/auth/cloud-platform
   ```
   Requires VM stop/start to take effect on some machine types.
6. **Pick a region**. Default to **`us-central1`** — has every model we need, lowest historical 503 rate for live audio. Fallback `us-east4`. Do not use `global` for the live voice service; regional endpoints are required.
7. **For local dev machines**, run once per developer:
   ```
   gcloud auth application-default login
   ```
   Then mount `~/.config/gcloud` into the Docker backend container, or store an SA JSON key and set `GOOGLE_APPLICATION_CREDENTIALS` in the dev `.env`.

### Phase 0 verification

Inside the API container (on the GCE VM), this should succeed:
```
docker compose exec api python -c "
from google import genai
c = genai.Client(vertexai=True, project='<PROJECT_ID>', location='us-central1')
r = c.models.generate_content(model='google/gemini-2.5-flash', contents='ping')
print(r.text)
"
```
If it prints anything, ADC + Vertex + quota are all good. If it raises, fix the cause before writing any code.

---

## Phase 1 — Config scaffolding + background calls (low risk, high value)

These four call sites are small, independent, and either user-blocking or already degrade silently. Migrating them first gets us ~80% of the reliability win with ~20% of the risk.

### 1a. Config

**`backend/app/core/config.py`** — add:
```python
google_cloud_project: str = ""
google_cloud_location: str = "us-central1"
gemini_use_vertex: bool = False   # feature flag; flip per call site or globally
```

**`backend/.env` / docker-compose environment** — add:
```
GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_USE_VERTEX=true
```
Keep `GEMINI_API_KEY` intact throughout Phase 1 — it's the fallback path.

### 1b. Client helper

**New file `backend/app/core/gemini_client.py`**:
```python
def make_genai_client(*, prefer_vertex: bool = True):
    """Return a google-genai Client. Vertex if configured and prefer_vertex;
    otherwise API-key. Raises if neither is configured."""
```

Single choke point for client construction. Lets us flip per call site via a flag or kwarg, and test with both paths.

### 1c. Migrate call sites (one commit per, order of safety)

1. **Custom prompt generator** — `api/routers/store/ai.py:97`
   - Swap client construction to `make_genai_client()`.
   - Change model to `"google/gemini-2.5-flash"` when Vertex, `"gemini-2.5-flash"` when API (note: no `google/` prefix on the API side).
   - Failure mode is already a visible error toast; perfect canary.

2. **Menu image extract** — `api/routers/store/menu.py:385`
   - Same swap. Keep multimodal payload shape — it's identical between surfaces.

3. **Note verify** — `voice/tools.py:249`
   - Same swap.

4. **Conversation monitor** — `voice/monitor.py` + `api/routers/voice/ws.py:182`
   - Same swap. Also kill the dead dataclass default in `monitor.py:61`.
   - Update `settings.voice_monitor_model` default to `google/gemini-2.5-flash` (was `gemini-3.1-flash-lite-preview`).

### 1d. Phase 1 acceptance

- [ ] Create a new order via voice, verify `Note verify:` log lines show `200 OK` against the Vertex endpoint (look for `aiplatform.googleapis.com` in httpx logs).
- [ ] Click **Generate** on an AI custom rule. Succeeds without a 503 during US business hours (the old model's worst window).
- [ ] Upload a menu image. Item extraction completes.
- [ ] `docker compose logs api 2>&1 | grep 503` returns nothing for 24 hours.

**Rollback**: flip `GEMINI_USE_VERTEX=false`, redeploy. Zero code changes, instant.

---

## Phase 2 — Live voice pipeline (biggest payoff, real risk)

This is the voice-bot-can't-start 503 case. The change is small in surface area but touches the hottest codepath.

### 2a. Code change

**`backend/app/voice/pipeline.py`** — replace:
```python
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService, GeminiVADParams
```
with a conditional import + factory:
```python
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService, GeminiVADParams
from pipecat.services.google.gemini_live.vertex.llm import GeminiLiveVertexLLMService
```

Build the LLM service based on the flag:
```python
if settings.gemini_use_vertex:
    llm = GeminiLiveVertexLLMService(
        project_id=settings.google_cloud_project,
        location=settings.google_cloud_location,
        # credentials / credentials_path omitted → ADC on GCE VM
        system_instruction=system_prompt,
        tools=tools,
        settings=GeminiLiveVertexLLMService.Settings(
            model="google/gemini-live-2.5-flash-native-audio",   # GA
            voice=voice_id,
            vad=GeminiVADParams(...same as before...),
        ),
    )
else:
    llm = GeminiLiveLLMService(...)  # existing Gemini API path, unchanged
```

### 2b. Config

- Add `voice_llm_model_vertex: str = "google/gemini-live-2.5-flash-native-audio"` to `config.py` so it's not hardcoded inside `pipeline.py`.
- Keep `voice_llm_model` for the API-key path.

### 2c. Things to verify post-switch (known Vertex differences)

From the installed pipecat source + docs:

- **History config is ignored on Vertex** (handled by pipecat). Should be a no-op for us.
- **File API is unavailable on Vertex**. We don't use it. Double-check no code calls `llm.file_api` — a `NotImplementedError` would surface.
- **Some transcription messages differ**. Our `user_turn_stopped` / `assistant_turn_stopped` handlers should still fire; verify by watching `Transcription:user` debug lines from pipecat after a test call.
- **Model ID prefix**. Must be `google/…`. Getting this wrong = 404.
- **OAuth token lifetime is 1h**. `GeminiLiveVertexLLMService._get_credentials` auto-refreshes. Verify a call that crosses the 1h mark still works (long-running session, unlikely in practice but worth noting).

### 2d. Phase 2 acceptance

- [ ] Start a voice session. Bot greets within normal TTFB (<1s).
- [ ] Add item, modify item, set delivery address, checkout — all tool calls succeed.
- [ ] `docker compose logs api 2>&1 | grep -iE "503|unavailable"` empty across 10 voice sessions.
- [ ] `GeminiLiveLLMService` warnings/errors absent from logs; replaced with `GeminiLiveVertexLLMService` counterparts.
- [ ] Cancel-race recovery loop (the `FunctionCallCancelObserver` we built earlier) still fires correctly — pipecat says no behavioral difference here.

**Rollback**: flip `GEMINI_USE_VERTEX=false`, redeploy. Gemini API path is kept alive through all of Phase 2.

---

## Phase 3 — Cleanup (after 1–2 weeks of stable production)

Only after both phases are healthy in prod:

1. Remove the `GEMINI_USE_VERTEX` feature flag + all the conditional branches.
2. Remove `GeminiLiveLLMService` import and the `else` branch in `pipeline.py`.
3. Remove the API-key path from the client helper.
4. Remove `GEMINI_API_KEY` / `GOOGLE_API_KEY` env vars from compose and docs (unless something still needs them).
5. Update `CLAUDE.md` — change the "Key Environment Variables" section to reflect Vertex auth.
6. Delete dead dataclass default at `voice/monitor.py:61`.

---

## Open questions / decisions to make before starting

1. **Reuse existing GCP project or create a new one?** Reuse is faster; dedicated is cleaner for cost attribution and blast radius. Default: reuse.
2. **Region: `us-central1` vs something closer to customers?** us-central1 has the best model availability. Latency to US users is fine; global customers would see a bit more. Default: `us-central1`.
3. **Provisioned Throughput — buy it now or wait?** Wait. Only buy when we're actually hitting quota under Vertex's default per-project limits. The whole point of this migration is that default Vertex capacity already dwarfs what we need.
4. **Do we also move `gemini-3.1-flash-live-preview` → `google/gemini-live-2.5-flash-native-audio` as part of Phase 2?** Yes. The native-audio GA model is specifically why Vertex is attractive for the voice path. Keeping preview on Vertex would give us new auth without the reliability win.
5. **Local dev auth UX.** `gcloud auth application-default login` every dev, or ship an SA key in `.env`? ADC login is more secure; SA key is more portable. Default: ADC login, document the one-time command in `README_run.md`.

---

## Cost estimate (rough, order-of-magnitude)

Assumes 100 voice orders/day, avg 3 minutes each.

- **Live voice** (`gemini-live-2.5-flash-native-audio`): input audio + output audio + tool tokens. At current Vertex pricing ~$0.50–$1.50 per 1M tokens for audio, a 3-min call ≈ 6k tokens ≈ $0.003–0.01 per call. **≈ $1–3/day at 100 calls.**
- **Monitor + note verify** (text, `gemini-2.5-flash`): ~500 tokens per bot turn, 5 turns/call, 2 checks/turn = 5k tokens/call. ≈ **$0.10–0.30/day**.
- **Menu image extract / custom prompt generator**: usage-driven, probably a handful of calls per store per week. Negligible.

**Total order-of-magnitude: single-digit dollars/day at the current scale.** Monitor actual cost in Billing → Reports after one full day of prod traffic.

---

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| ADC doesn't pick up the attached SA on the VM | Medium | Run the Phase 0 verification command in prod before migrating any code. |
| Live voice latency higher on Vertex | Low | us-central1 is comparable. If it regresses, fall back via flag; investigate. |
| Billing surprise | Low–Medium | Set a GCP budget alert at $50/mo; review after 1 week. |
| `google/` model ID typo → 404 | Low | Defined as a constant in `config.py`, not hardcoded at each site. |
| Pipecat behavior differences break the UX (transcription, cancel recovery) | Low | Acceptance tests in Phase 2d explicitly check. |
| OAuth token refresh fails mid-call | Very low | Pipecat handles it; 1h lifetime covers any call we'd make. |

---

## Execution order (summary)

1. [ ] Phase 0 GCP setup (manual, ~30 min).
2. [ ] Phase 0 verification command passes in prod.
3. [ ] Phase 1a config scaffold committed.
4. [ ] Phase 1b client helper committed.
5. [ ] Phase 1c migrate prompt generator → menu image extract → note verify → monitor (one commit each).
6. [ ] Phase 1d acceptance, 24h burn-in with flag on.
7. [ ] Phase 2 live voice migration.
8. [ ] Phase 2d acceptance, 1–2 weeks burn-in.
9. [ ] Phase 3 cleanup: drop the flag, remove the Gemini API path, update docs.

Reversible at any point via `GEMINI_USE_VERTEX=false` until Phase 3.
