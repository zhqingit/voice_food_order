import 'dart:async';
import 'dart:io' show Platform;
import 'dart:typed_data';

import 'package:audio_session/audio_session.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/order_models.dart';
import '../../data/order_repository.dart';
import '../../data/voice_audio_player.dart';
import '../../data/voice_audio_recorder.dart';
import '../../data/voice_session_repository.dart';
import '../../data/voice_ws_client.dart';

class TranscriptEntry {
  final String speaker; // 'user' or 'assistant'
  final String text;

  const TranscriptEntry({required this.speaker, required this.text});
}

/// A live order item received from the backend during an active session.
class LiveOrderItem {
  final String name;
  final int quantity;
  final double lineTotal;
  final String? note;

  const LiveOrderItem({required this.name, required this.quantity, required this.lineTotal, this.note});

  factory LiveOrderItem.fromJson(Map<String, dynamic> json) {
    return LiveOrderItem(
      name: json['name'] as String? ?? 'Item',
      quantity: json['quantity'] as int? ?? 1,
      lineTotal: (json['line_total'] as num?)?.toDouble() ?? 0,
      note: json['note'] as String?,
    );
  }
}

/// Live order summary received via WebSocket during an active session.
class LiveOrderSummary {
  final String status;
  final double subtotal;
  final double tax;
  final double total;
  final List<LiveOrderItem> items;

  const LiveOrderSummary({required this.status, required this.subtotal, required this.tax, required this.total, required this.items});

  factory LiveOrderSummary.fromJson(Map<String, dynamic> json) {
    final itemsList = (json['items'] as List<dynamic>?)
        ?.map((e) => LiveOrderItem.fromJson(e as Map<String, dynamic>))
        .toList() ?? [];
    return LiveOrderSummary(
      status: json['status'] as String? ?? 'draft',
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0,
      tax: (json['tax'] as num?)?.toDouble() ?? 0,
      total: (json['total'] as num?)?.toDouble() ?? 0,
      items: itemsList,
    );
  }
}

class VoiceUiState {
  final bool connecting;
  final bool connected;
  final String? sessionId;
  final String? error;
  final List<String> logs;
  final List<TranscriptEntry> transcripts;

  // Live order state (updated during active session)
  final LiveOrderSummary? liveOrder;

  // Post-session state
  final bool sessionEnded;
  final OrderOut? orderSummary;
  final List<OrderItemOut>? orderItems;
  final int? rating;
  final bool ratingSubmitted;
  final bool reviewSubmitted;

  const VoiceUiState({
    required this.connecting,
    required this.connected,
    required this.sessionId,
    required this.error,
    required this.logs,
    required this.transcripts,
    required this.liveOrder,
    required this.sessionEnded,
    required this.orderSummary,
    required this.orderItems,
    required this.rating,
    required this.ratingSubmitted,
    required this.reviewSubmitted,
  });

  factory VoiceUiState.initial() => const VoiceUiState(
        connecting: false,
        connected: false,
        sessionId: null,
        error: null,
        logs: <String>[],
        transcripts: <TranscriptEntry>[],
        liveOrder: null,
        sessionEnded: false,
        orderSummary: null,
        orderItems: null,
        rating: null,
        ratingSubmitted: false,
        reviewSubmitted: false,
      );

  VoiceUiState copyWith({
    bool? connecting,
    bool? connected,
    String? sessionId,
    String? error,
    List<String>? logs,
    List<TranscriptEntry>? transcripts,
    LiveOrderSummary? liveOrder,
    bool clearLiveOrder = false,
    bool? sessionEnded,
    OrderOut? orderSummary,
    List<OrderItemOut>? orderItems,
    int? rating,
    bool? ratingSubmitted,
    bool? reviewSubmitted,
  }) {
    return VoiceUiState(
      connecting: connecting ?? this.connecting,
      connected: connected ?? this.connected,
      sessionId: sessionId ?? this.sessionId,
      error: error,
      logs: logs ?? this.logs,
      transcripts: transcripts ?? this.transcripts,
      liveOrder: clearLiveOrder ? null : (liveOrder ?? this.liveOrder),
      sessionEnded: sessionEnded ?? this.sessionEnded,
      orderSummary: orderSummary ?? this.orderSummary,
      orderItems: orderItems ?? this.orderItems,
      rating: rating ?? this.rating,
      ratingSubmitted: ratingSubmitted ?? this.ratingSubmitted,
      reviewSubmitted: reviewSubmitted ?? this.reviewSubmitted,
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

      // 2. Configure iOS audio session for simultaneous playback + recording
      //    through the speaker (not earpiece).
      if (Platform.isIOS) {
        final audioSession = await AudioSession.instance;
        await audioSession.configure(AudioSessionConfiguration(
          avAudioSessionCategory: AVAudioSessionCategory.playAndRecord,
          avAudioSessionCategoryOptions:
              AVAudioSessionCategoryOptions.defaultToSpeaker |
              AVAudioSessionCategoryOptions.allowBluetooth,
          avAudioSessionMode: AVAudioSessionMode.voiceChat,
        ));
        await audioSession.setActive(true);
      }

      // 3. Set up audio player (native AudioTrack).
      final audioPlayer = ref.read(voiceAudioPlayerProvider);
      await audioPlayer.setup();

      // 4. Start mic recorder BEFORE WebSocket so it holds audio focus first.
      final recorder = ref.read(voiceAudioRecorderProvider);
      final ws = ref.read(voiceWsClientProvider);

      final granted = await recorder.start(
        onChunk: (Uint8List chunk) {
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

      // 5. Mute mic while bot speaks to prevent echo feedback.
      //    Barge-in is handled via the interrupt() method (tap-to-interrupt).
      audioPlayer.onPlayingChanged = (playing) {
        if (playing) {
          recorder.pause();
        } else {
          recorder.resume();
        }
      };

      // 6. Connect WebSocket with sessionId so backend can link order.
      await ws.connect(storeId: storeId, sessionId: session.id, accessToken: bundle.accessToken);

      _wsSub = ws.events.listen((evt) {
        // Parse transcript events from the backend.
        final type = evt['type'] as String?;
        if (type == 'transcript_user') {
          _addTranscript('user', evt['text'] as String? ?? '');
        } else if (type == 'transcript_assistant') {
          _addTranscript('assistant', evt['text'] as String? ?? '');
        } else if (type == 'interruption') {
          ref.read(voiceAudioPlayerProvider).clearBuffer();
        } else if (type == 'order_update') {
          final orderJson = evt['order'] as Map<String, dynamic>?;
          if (orderJson != null) {
            state = state.copyWith(liveOrder: LiveOrderSummary.fromJson(orderJson));
          }
        } else if (type == 'closed' && state.connected) {
          stop();
        }
      });

      // 7. Subscribe to audio stream and feed to player.
      _audioSub = ws.audioStream.listen((bytes) {
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

  Future<void> submitReview(String review) async {
    final sessionId = state.sessionId;
    if (sessionId == null || review.trim().isEmpty) return;

    try {
      await ref.read(voiceSessionRepositoryProvider).submitReview(sessionId: sessionId, review: review.trim());
      state = state.copyWith(reviewSubmitted: true);
    } catch (e) {
      _append('submit review failed: $e');
    }
  }

  void resetSession() {
    state = VoiceUiState.initial();
  }

  void _addTranscript(String speaker, String text) {
    if (text.isEmpty) return;
    final list = [...state.transcripts];
    // Merge consecutive entries from the same speaker.
    if (list.isNotEmpty && list.last.speaker == speaker) {
      list[list.length - 1] = TranscriptEntry(
        speaker: speaker,
        text: '${list.last.text} $text',
      );
    } else {
      list.add(TranscriptEntry(speaker: speaker, text: text));
    }
    state = state.copyWith(transcripts: list);
  }

  void _append(String line) {
    final next = [...state.logs, line];
    final capped = next.length > 200 ? next.sublist(next.length - 200) : next;
    state = state.copyWith(logs: capped);
  }
}
