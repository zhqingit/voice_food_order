import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/voice_audio_player.dart';
import '../../data/voice_audio_recorder.dart';
import '../../data/voice_session_repository.dart';
import '../../data/voice_ws_client.dart';

class VoiceUiState {
  final bool connecting;
  final bool connected;
  final String? sessionId;
  final String? error;
  final List<String> logs;

  const VoiceUiState({
    required this.connecting,
    required this.connected,
    required this.sessionId,
    required this.error,
    required this.logs,
  });

  factory VoiceUiState.initial() => const VoiceUiState(
        connecting: false,
        connected: false,
        sessionId: null,
        error: null,
        logs: <String>[],
      );

  VoiceUiState copyWith({
    bool? connecting,
    bool? connected,
    String? sessionId,
    String? error,
    List<String>? logs,
  }) {
    return VoiceUiState(
      connecting: connecting ?? this.connecting,
      connected: connected ?? this.connected,
      sessionId: sessionId ?? this.sessionId,
      error: error,
      logs: logs ?? this.logs,
    );
  }
}

final voiceSessionRepositoryProvider = Provider<VoiceSessionRepository>((ref) {
  return VoiceSessionRepository(ref.watch(apiClientProvider).dio);
});

final voiceWsClientProvider = Provider<VoiceWsClient>((ref) {
  final client = VoiceWsClient();
  ref.onDispose(() => client.dispose());
  return client;
});

final voiceAudioPlayerProvider = Provider<VoiceAudioPlayer>((ref) {
  final player = VoiceAudioPlayer();
  ref.onDispose(() => player.dispose());
  return player;
});

final voiceAudioRecorderProvider = Provider<VoiceAudioRecorder>((ref) {
  final r = VoiceAudioRecorder();
  ref.onDispose(() => r.dispose());
  return r;
});

final voiceControllerProvider = NotifierProvider<VoiceController, VoiceUiState>(VoiceController.new);

class VoiceController extends Notifier<VoiceUiState> {
  StreamSubscription? _wsSub;
  StreamSubscription? _audioSub;

  @override
  VoiceUiState build() {
    return VoiceUiState.initial();
  }

  Future<void> start({required String storeId}) async {
    if (state.connecting || state.connected) return;

    state = state.copyWith(connecting: true, error: null);

    final tokenStore = ref.read(tokenStoreProvider);
    final bundle = await tokenStore.read();
    if (bundle == null) {
      state = state.copyWith(connecting: false, error: 'Not authenticated. Please login first.');
      return;
    }

    try {
      final repo = ref.read(voiceSessionRepositoryProvider);
      final session = await repo.create(storeId: storeId, channel: 'voice');

      _append('created session ${session.id}');

      final ws = ref.read(voiceWsClientProvider);
      await ws.connect(storeId: storeId, accessToken: bundle.accessToken);

      _wsSub = ws.events.listen((evt) {
        _append(evt.toString());
      });

      final audioPlayer = ref.read(voiceAudioPlayerProvider);
      _audioSub = ws.audioStream.listen((bytes) {
        audioPlayer.enqueue(bytes);
      });

      final recorder = ref.read(voiceAudioRecorderProvider);
      final granted = await recorder.start(
        onChunk: (Uint8List chunk) {
          // Forward PCM16 audio frames as binary WS messages.
          ws.sendBytes(chunk);
        },
      );

      if (!granted) {
        await stop();
        state = state.copyWith(error: 'Microphone permission not granted.');
        return;
      }

      _append('mic streaming started');

      state = state.copyWith(
        connecting: false,
        connected: true,
        sessionId: session.id,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(connecting: false, connected: false, error: e.toString());
    }
  }

  Future<void> stop() async {
    if (!state.connected && !state.connecting) return;

    final sessionId = state.sessionId;

    state = state.copyWith(connecting: false, connected: false);

    await _wsSub?.cancel();
    _wsSub = null;
    await _audioSub?.cancel();
    _audioSub = null;

    try {
      await ref.read(voiceAudioPlayerProvider).stop();
    } catch (_) {
      // ignore
    }

    try {
      await ref.read(voiceAudioRecorderProvider).stop();
    } catch (_) {
      // ignore
    }

    try {
      await ref.read(voiceWsClientProvider).disconnect();
    } catch (_) {
      // ignore
    }

    if (sessionId != null) {
      try {
        final ended = await ref.read(voiceSessionRepositoryProvider).end(sessionId: sessionId);
        _append('ended session ${ended.id}');
      } catch (e) {
        _append('end session failed: $e');
      }
    }
  }

  void _append(String line) {
    final next = [...state.logs, line];
    // cap log size
    final capped = next.length > 200 ? next.sublist(next.length - 200) : next;
    state = state.copyWith(logs: capped);
  }
}
