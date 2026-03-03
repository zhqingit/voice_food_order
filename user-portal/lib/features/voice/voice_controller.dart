import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/order_models.dart';
import '../../data/order_repository.dart';
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

  // Post-session state
  final bool sessionEnded;
  final OrderOut? orderSummary;
  final List<OrderItemOut>? orderItems;
  final int? rating;
  final bool ratingSubmitted;

  const VoiceUiState({
    required this.connecting,
    required this.connected,
    required this.sessionId,
    required this.error,
    required this.logs,
    required this.sessionEnded,
    required this.orderSummary,
    required this.orderItems,
    required this.rating,
    required this.ratingSubmitted,
  });

  factory VoiceUiState.initial() => const VoiceUiState(
        connecting: false,
        connected: false,
        sessionId: null,
        error: null,
        logs: <String>[],
        sessionEnded: false,
        orderSummary: null,
        orderItems: null,
        rating: null,
        ratingSubmitted: false,
      );

  VoiceUiState copyWith({
    bool? connecting,
    bool? connected,
    String? sessionId,
    String? error,
    List<String>? logs,
    bool? sessionEnded,
    OrderOut? orderSummary,
    List<OrderItemOut>? orderItems,
    int? rating,
    bool? ratingSubmitted,
  }) {
    return VoiceUiState(
      connecting: connecting ?? this.connecting,
      connected: connected ?? this.connected,
      sessionId: sessionId ?? this.sessionId,
      error: error,
      logs: logs ?? this.logs,
      sessionEnded: sessionEnded ?? this.sessionEnded,
      orderSummary: orderSummary ?? this.orderSummary,
      orderItems: orderItems ?? this.orderItems,
      rating: rating ?? this.rating,
      ratingSubmitted: ratingSubmitted ?? this.ratingSubmitted,
    );
  }
}

final voiceSessionRepositoryProvider = Provider<VoiceSessionRepository>((ref) {
  return VoiceSessionRepository(ref.watch(apiClientProvider).dio);
});

final orderRepositoryProvider = Provider<OrderRepository>((ref) {
  return OrderRepository(ref.watch(apiClientProvider).dio);
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
      // 1. Create voice session via REST API.
      final repo = ref.read(voiceSessionRepositoryProvider);
      final session = await repo.create(storeId: storeId, channel: 'voice');
      _append('created session ${session.id}');

      // 2. Set up audio player (native AudioTrack) FIRST.
      final audioPlayer = ref.read(voiceAudioPlayerProvider);
      await audioPlayer.setup();

      // 3. Start mic recorder BEFORE WebSocket so it holds audio focus first.
      final recorder = ref.read(voiceAudioRecorderProvider);
      final ws = ref.read(voiceWsClientProvider);
      int micChunkCount = 0;

      final granted = await recorder.start(
        onChunk: (Uint8List chunk) {
          micChunkCount++;
          if (micChunkCount <= 3 || micChunkCount % 100 == 0) {
            _append('mic: chunk#$micChunkCount, ${chunk.length}B');
          }
          ws.sendBytes(chunk);
        },
        onError: (e) {
          _append('mic error: $e');
          state = state.copyWith(error: 'Microphone stopped unexpectedly.');
          stop();
        },
      );

      if (!granted) {
        state = state.copyWith(connecting: false, error: 'Microphone permission not granted.');
        return;
      }
      _append('mic streaming started');

      // 4. Wire mic muting: pause mic while bot is speaking to prevent echo.
      audioPlayer.onPlayingChanged = (playing) {
        if (playing) {
          recorder.pause();
          _append('mic: paused (bot speaking)');
        } else {
          recorder.resume();
          _append('mic: resumed');
        }
      };

      // 5. Connect WebSocket with sessionId so backend can link order.
      await ws.connect(storeId: storeId, sessionId: session.id, accessToken: bundle.accessToken);

      _wsSub = ws.events.listen((evt) {
        _append(evt.toString());
        if (evt case {'type': 'closed'} when state.connected) {
          stop();
        }
      });

      // 6. Subscribe to audio stream and feed to player.
      int audioChunkCount = 0;
      int totalAudioBytes = 0;
      _audioSub = ws.audioStream.listen((bytes) {
        audioChunkCount++;
        totalAudioBytes += bytes.length;
        if (audioChunkCount % 50 == 1) {
          _append('audio: chunk#$audioChunkCount, total ${totalAudioBytes}B');
        }
        audioPlayer.enqueue(bytes);
      });

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
      final player = ref.read(voiceAudioPlayerProvider);
      player.onPlayingChanged = null;
      await player.stop();
    } catch (_) {}

    try {
      await ref.read(voiceAudioRecorderProvider).stop();
    } catch (_) {}

    try {
      await ref.read(voiceWsClientProvider).disconnect();
    } catch (_) {}

    if (sessionId != null) {
      try {
        final ended = await ref.read(voiceSessionRepositoryProvider).end(sessionId: sessionId);
        _append('ended session ${ended.id}');

        // Fetch order summary if an order was created during the session.
        if (ended.orderId != null) {
          try {
            final orderRepo = ref.read(orderRepositoryProvider);
            final order = await orderRepo.getOrder(ended.orderId!);
            final items = await orderRepo.getOrderItems(ended.orderId!);
            state = state.copyWith(
              sessionEnded: true,
              orderSummary: order,
              orderItems: items,
            );
          } catch (e) {
            _append('fetch order failed: $e');
            state = state.copyWith(sessionEnded: true);
          }
        } else {
          state = state.copyWith(sessionEnded: true);
        }
      } catch (e) {
        _append('end session failed: $e');
        state = state.copyWith(sessionEnded: true);
      }
    } else {
      state = state.copyWith(sessionEnded: true);
    }
  }

  Future<void> submitRating(int rating) async {
    final sessionId = state.sessionId;
    if (sessionId == null) return;

    state = state.copyWith(rating: rating);

    try {
      await ref.read(voiceSessionRepositoryProvider).submitRating(sessionId: sessionId, rating: rating);
      state = state.copyWith(ratingSubmitted: true);
    } catch (e) {
      _append('submit rating failed: $e');
    }
  }

  void resetSession() {
    state = VoiceUiState.initial();
  }

  void _append(String line) {
    final next = [...state.logs, line];
    final capped = next.length > 200 ? next.sublist(next.length - 200) : next;
    state = state.copyWith(logs: capped);
  }
}
