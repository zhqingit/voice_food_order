import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  getMe,
  updateMe,
  listAIPrompts,
  generateAIPrompt,
  saveAIPrompts,
  type StoreMe,
  type AIPromptRule,
} from '../api/storeApi'

type RuleRow = AIPromptRule & {
  // Client-only id for stable React keys across edits.
  id: string
  generating?: boolean
}

function newRow(seed?: Partial<AIPromptRule>): RuleRow {
  return {
    id: Math.random().toString(36).slice(2, 10),
    raw: seed?.raw ?? '',
    generated: seed?.generated ?? '',
  }
}

function stripId(r: RuleRow): AIPromptRule {
  return { raw: r.raw, generated: r.generated }
}

function rulesEqual(a: RuleRow[], b: RuleRow[]): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i].raw !== b[i].raw || a[i].generated !== b[i].generated) return false
  }
  return true
}

export function AIRoute(): React.JSX.Element {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [me, setMe] = useState<StoreMe | null>(null)
  const [voiceTone, setVoiceTone] = useState<string | null>(null)

  const [rules, setRules] = useState<RuleRow[]>([])
  const [loadedRules, setLoadedRules] = useState<RuleRow[]>([])
  const [savingRules, setSavingRules] = useState(false)

  const voiceDirty = useMemo(
    () => me != null && voiceTone !== (me.voice_tone ?? null),
    [me, voiceTone],
  )

  const rulesDirty = useMemo(() => !rulesEqual(rules, loadedRules), [rules, loadedRules])

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const [meData, prompts] = await Promise.all([getMe(), listAIPrompts()])
        setMe(meData)
        setVoiceTone(meData.voice_tone ?? null)
        const rows = prompts.map((p) => newRow(p))
        setRules(rows)
        setLoadedRules(rows)
      } catch {
        setError(t('ai.failedLoad'))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function handleSaveVoice(): Promise<void> {
    setError(null)
    setMessage(null)
    try {
      const updated = await updateMe({ voice_tone: voiceTone })
      setMe(updated)
      setMessage(t('ai.saved'))
    } catch {
      setError(t('ai.failedSave'))
    }
  }

  function handleAddRule(): void {
    setRules((prev) => [...prev, newRow()])
  }

  function handleRemoveRule(id: string): void {
    setRules((prev) => prev.filter((r) => r.id !== id))
  }

  function handleEditRule(id: string, patch: Partial<AIPromptRule>): void {
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)))
  }

  async function handleGenerateRule(id: string): Promise<void> {
    const row = rules.find((r) => r.id === id)
    if (!row || !row.raw.trim()) {
      setError(t('ai.rawRequired'))
      return
    }
    setError(null)
    setMessage(null)
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, generating: true } : r)))
    try {
      const out = await generateAIPrompt(row.raw.trim())
      setRules((prev) => prev.map((r) => (r.id === id ? { ...r, generated: out, generating: false } : r)))
    } catch {
      setRules((prev) => prev.map((r) => (r.id === id ? { ...r, generating: false } : r)))
      setError(t('ai.failedGenerate'))
    }
  }

  async function handleSaveRules(): Promise<void> {
    setError(null)
    setMessage(null)
    setSavingRules(true)
    try {
      const saved = await saveAIPrompts(rules.map(stripId))
      const rows = saved.map((p) => newRow(p))
      setRules(rows)
      setLoadedRules(rows)
      setMessage(t('ai.savedAndActive'))
    } catch {
      setError(t('ai.failedSave'))
    } finally {
      setSavingRules(false)
    }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>{t('ai.title')}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: 13 }}>
          {t('ai.subtitle')}
        </p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
      {message && <div className="alert alert-success" style={{ marginBottom: 16 }}>{message}</div>}

      {loading ? (
        <div style={{ color: 'var(--color-text-secondary)' }}>{t('common.loading')}</div>
      ) : (
        <>
          {/* Voice Tone */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <h2>{t('ai.voiceTone')}</h2>
            </div>
            <div className="card-body">
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '0 0 12px' }}>
                {t('ai.voiceToneDesc')}
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {[
                  { value: null, label: t('ai.voiceDefault') },
                  { value: 'female', label: t('ai.voiceFemale') },
                  { value: 'male', label: t('ai.voiceMale') },
                ].map((opt) => (
                  <button
                    key={opt.value ?? 'default'}
                    type="button"
                    className={`btn btn-sm ${voiceTone === opt.value ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setVoiceTone(opt.value)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className={`btn ${voiceDirty ? 'btn-warning' : 'btn-primary'}`}
                  style={voiceDirty ? { background: '#f59e0b', color: '#fff' } : undefined}
                  disabled={!voiceDirty}
                  onClick={() => void handleSaveVoice()}
                >
                  {voiceDirty ? `● ${t('ai.save')}` : t('ai.save')}
                </button>
              </div>
            </div>
          </div>

          {/* Custom Rules Table */}
          <div className="card">
            <div className="card-header">
              <h2>{t('ai.customRules')}</h2>
            </div>
            <div className="card-body">
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', margin: '0 0 16px' }}>
                {t('ai.customRulesDesc')}
              </p>

              {/* Header row */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 140px',
                  gap: 12,
                  padding: '0 4px 8px',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--color-text-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                <div>{t('ai.columnRaw')}</div>
                <div>{t('ai.columnGenerated')}</div>
                <div style={{ textAlign: 'right' }}>{t('ai.columnActions')}</div>
              </div>

              {/* Body rows */}
              {rules.length === 0 && (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-text-secondary)', fontSize: 13 }}>
                  {t('ai.emptyRules')}
                </div>
              )}
              {rules.map((row) => (
                <div
                  key={row.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 140px',
                    gap: 12,
                    padding: '12px 4px',
                    borderBottom: '1px solid var(--color-border)',
                    alignItems: 'start',
                  }}
                >
                  <textarea
                    className="form-input"
                    rows={4}
                    value={row.raw}
                    placeholder={t('ai.rawPlaceholder')}
                    onChange={(e) => handleEditRule(row.id, { raw: e.target.value })}
                    style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
                  />
                  <textarea
                    className="form-input"
                    rows={4}
                    value={row.generated}
                    placeholder={t('ai.generatedPlaceholder')}
                    onChange={(e) => handleEditRule(row.id, { generated: e.target.value })}
                    style={{
                      width: '100%',
                      resize: 'vertical',
                      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                      fontSize: 12.5,
                    }}
                  />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'stretch' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => void handleGenerateRule(row.id)}
                      disabled={row.generating || !row.raw.trim()}
                    >
                      {row.generating ? t('ai.generating') : (row.generated ? t('ai.regenerate') : t('ai.generate'))}
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleRemoveRule(row.id)}
                    >
                      {t('ai.delete')}
                    </button>
                  </div>
                </div>
              ))}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
                <button type="button" className="btn btn-secondary" onClick={handleAddRule}>
                  + {t('ai.addRule')}
                </button>
                <button
                  type="button"
                  className={`btn ${rulesDirty ? 'btn-warning' : 'btn-primary'}`}
                  style={rulesDirty ? { background: '#f59e0b', color: '#fff' } : undefined}
                  disabled={!rulesDirty || savingRules}
                  onClick={() => void handleSaveRules()}
                >
                  {rulesDirty ? `● ${t('ai.saveAll')}` : t('ai.saveAll')}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
