import 'dart:async';
import 'dart:io' show Platform;
import 'dart:typed_data';

import 'package:audio_session/audio_session.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/order_models.dart';
import '../../data/order_repository.dart';
import '../../data/voice_audio_bridge.dart';
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
  final String? variant;

  const LiveOrderItem({
    required this.name,
    required this.quantity,
    required this.lineTotal,
    this.note,
    this.variant,
  });

  factory LiveOrderItem.fromJson(Map<String, dynamic> json) {
    return LiveOrderItem(
      name: json['name'] as String? ?? 'Item',
      quantity: json['quantity'] as int? ?? 1,
      lineTotal: (json['line_total'] as num?)?.toDouble() ?? 0,
      note: json['note'] as String?,
      variant: json['variant'] as String?,
    );
  }
}

/// Live order summary received via WebSocket during an active session.
class LiveOrderSummary {
  final String? orderId;
  final String status;
  final double subtotal;
  final double tax;
  final double total;
  final List<LiveOrderItem> items;
  final String? fulfillmentType;
  final String? deliveryAddress;

  const LiveOrderSummary({
    required this.orderId,
    required this.status,
    required this.subtotal,
    required this.tax,
    required this.total,
    required this.items,
    required this.fulfillmentType,
    required this.deliveryAddress,
  });

  factory LiveOrderSummary.fromJson(Map<String, dynamic> json) {
    final itemsList = (json['items'] as List<dynamic>?)
        ?.map((e) => LiveOrderItem.fromJson(e as Map<String, dynamic>))
        .toList() ?? [];
    return LiveOrderSummary(
      orderId: json['order_id'] as String?,
      status: json['status'] as String? ?? 'draft',
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0,
      tax: (json['tax'] as num?)?.toDouble() ?? 0,
      total: (json['total'] as num?)?.toDouble() ?? 0,
      items: itemsList,
      fulfillmentType: json['fulfillment_type'] as String?,
      deliveryAddress: json['delivery_address'] as String?,
    );
  }

  LiveOrderSummary copyWith({String? deliveryAddress}) {
    return LiveOrderSummary(
      orderId: orderId,
      status: status,
      subtotal: subtotal,
      tax: tax,
      total: total,
      items: items,
      fulfillmentType: fulfillmentType,
      deliveryAddress: deliveryAddress ?? this.deliveryAddress,
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

final voiceAudioBridgeProvider = Provider<VoiceAudioBridge>((ref) {
  final bridge = VoiceAudioBridge();
  ref.onDispose(() => bridge.dispose());
  return bridge;
});

/// Voice controller scoped to a single store screen.
///
/// `autoDispose` + `family(storeId)`: each store gets its own fresh state, and
/// once the voice screen is gone (back button, Android back, iOS swipe-back)
/// the provider is disposed and [VoiceController._teardown] releases the mic,
/// WebSocket and server-side voice session.
final voiceControllerProvider =
    NotifierProvider.autoDispose.family<VoiceController, VoiceUiState, String>(VoiceController.new);

class VoiceController extends AutoDisposeFamilyNotifier<VoiceUiState, String> {
  StreamSubscription? _wsSub;
  StreamSubscription? _audioSub;

  // Dependencies captured in build() so teardown in onDispose never has to
  // touch `ref`.
  late VoiceSessionRepository _sessionRepo;
  late VoiceAudioBridge _bridge;
  late VoiceWsClient _ws;

  // Resources this controller currently owns. Teardown only releases what is
  // flagged here, so a late teardown never stops another screen's session on
  // the shared bridge / WebSocket client.
  bool _bridgeOwned = false;
  bool _wsOwned = false;
  String? _activeSessionId; // created on server and not yet ended

  bool _disposed = false;

  @override
  VoiceUiState build(String storeId) {
    _sessionRepo = ref.read(voiceSessionRepositoryProvider);
    _bridge = ref.read(voiceAudioBridgeProvider);
    _ws = ref.read(voiceWsClientProvider);

    ref.onDispose(() {
      _disposed = true;
      _teardown();
    });

    return VoiceUiState.initial();
  }

  /// Synchronously release every resource this controller owns. Async work
  /// (closing sockets, stopping audio, ending the server session) is
  /// fire-and-forget. Never touches `state` or other providers, so it is safe
  /// to call from `ref.onDispose`. Idempotent.
  void _teardown() {
    final wsSub = _wsSub;
    final audioSub = _audioSub;
    _wsSub = null;
    _audioSub = null;
    if (wsSub != null) unawaited(wsSub.cancel());
    if (audioSub != null) unawaited(audioSub.cancel());

    if (_bridgeOwned) {
      _bridgeOwned = false;
      _bridge.onRecordedChunk = null;
      _bridge.onRecordError = null;
      _bridge.onPlayingChanged = null;
      unawaited(_bridge.stopSession().catchError((_) {}));
    }

    if (_wsOwned) {
      _wsOwned = false;
      unawaited(_ws.disconnect().catchError((_) {}));
    }

    final sessionId = _activeSessionId;
    _activeSessionId = null;
    if (sessionId != null) {
      unawaited(_sessionRepo.end(sessionId: sessionId).then((_) {}, onError: (_) {}));
    }
  }

  Future<void> start() async {
    if (_disposed || state.connecting || state.connected) return;

    state = state.copyWith(connecting: true, error: null);

    final tokenStore = ref.read(tokenStoreProvider);
    final bundle = await tokenStore.read();
    if (_disposed) return;
    if (bundle == null) {
      state = state.copyWith(connecting: false, error: 'Not authenticated. Please login first.');
      return;
    }

    try {
      // 1. Create voice session via REST API.
      final session = await _sessionRepo.create(storeId: arg, channel: 'voice');
      _activeSessionId = session.id;
      if (_disposed) {
        _teardown();
        return;
      }
      _append('created session ${session.id}');

      // 2. Configure iOS audio session BEFORE starting the audio bridge so
      //    the single AVAudioEngine starts with voiceChat mode + defaultToSpeaker.
      if (Platform.isIOS) {
        await _configureIosAudioSession();
        if (_disposed) {
          _teardown();
          return;
        }
      }

      // 3. Start the unified audio bridge (recording + playback).
      //    On iOS this creates one AVAudioEngine; on Android it delegates to
      //    the existing VoiceAudioPlayer + VoiceAudioRecorder.
      final bridge = _bridge;
      final ws = _ws;

      bridge.onRecordedChunk = (Uint8List chunk) {
        ws.sendBytes(chunk);
      };
      bridge.onRecordError = (e) {
        if (_disposed) return;
        _append('mic error: $e');
        state = state.copyWith(error: 'Microphone stopped unexpectedly.');
        stop();
      };

      _bridgeOwned = true;
      final granted = await bridge.startSession();
      if (_disposed) {
        _teardown();
        return;
      }
      if (!granted) {
        state = state.copyWith(connecting: false, error: 'Microphone permission not granted.');
        return;
      }

      // 4. Connect WebSocket with sessionId so backend can link order.
      _wsOwned = true;
      await ws.connect(storeId: arg, sessionId: session.id, accessToken: bundle.accessToken);
      if (_disposed) {
        _teardown();
        return;
      }

      _wsSub = ws.events.listen((evt) {
        if (_disposed) return;
        // Parse transcript events from the backend.
        final type = evt['type'] as String?;
        if (type == 'transcript_user') {
          _addTranscript('user', evt['text'] as String? ?? '');
        } else if (type == 'transcript_assistant') {
          _addTranscript('assistant', evt['text'] as String? ?? '');
        } else if (type == 'interruption') {
          bridge.clearPlayback();
        } else if (type == 'order_update') {
          final orderJson = evt['order'] as Map<String, dynamic>?;
          if (orderJson != null) {
            state = state.copyWith(liveOrder: LiveOrderSummary.fromJson(orderJson));
          }
        } else if (type == 'closed' && state.connected) {
          stop();
        }
      });

      // 5. Subscribe to audio stream and feed to bridge for playback.
      _audioSub = ws.audioStream.listen((bytes) {
        bridge.feedAudio(bytes);
      });

      state = state.copyWith(
        connecting: false,
        connected: true,
        sessionId: session.id,
        error: null,
      );
    } catch (e) {
      if (_disposed) {
        _teardown();
        return;
      }
      state = state.copyWith(connecting: false, connected: false, error: e.toString());
    }
  }

  Future<void> stop() async {
    if (_disposed) return;
    if (!state.connected && !state.connecting) return;

    final sessionId = state.sessionId;
    // stop() ends the session itself (and fetches the order); make sure a
    // concurrent dispose does not end it a second time.
    if (_activeSessionId == sessionId) _activeSessionId = null;

    state = state.copyWith(connecting: false, connected: false);

    await _wsSub?.cancel();
    _wsSub = null;
    await _audioSub?.cancel();
    _audioSub = null;

    try {
      _bridgeOwned = false;
      _bridge.onRecordedChunk = null;
      _bridge.onRecordError = null;
      _bridge.onPlayingChanged = null;
      await _bridge.stopSession();
    } catch (_) {}

    try {
      _wsOwned = false;
      await _ws.disconnect();
    } catch (_) {}

    if (sessionId != null) {
      try {
        final ended = await _sessionRepo.end(sessionId: sessionId);
        if (_disposed) return;
        _append('ended session ${ended.id}');

        // Fetch order summary if an order was created during the session.
        if (ended.orderId != null) {
          try {
            final orderRepo = ref.read(orderRepositoryProvider);
            final order = await orderRepo.getOrder(ended.orderId!);
            final items = await orderRepo.getOrderItems(ended.orderId!);
            if (_disposed) return;
            state = state.copyWith(
              sessionEnded: true,
              orderSummary: order,
              orderItems: items,
            );
          } catch (e) {
            if (_disposed) return;
            _append('fetch order failed: $e');
            state = state.copyWith(sessionEnded: true);
          }
        } else {
          state = state.copyWith(sessionEnded: true);
        }
      } catch (e) {
        if (_disposed) return;
        _append('end session failed: $e');
        state = state.copyWith(sessionEnded: true);
      }
    } else {
      state = state.copyWith(sessionEnded: true);
    }
  }

  /// Persist an edited delivery address to the server. Updates local state
  /// optimistically so the field reflects the edit immediately; the next
  /// `order_update` from the bot will overwrite with server state.
  Future<void> updateDeliveryAddress(String address) async {
    final live = state.liveOrder;
    if (live == null || live.orderId == null) return;
    // Optimistic: reflect the edit locally so the TextField stays stable.
    state = state.copyWith(liveOrder: live.copyWith(deliveryAddress: address));
    try {
      await ref.read(orderRepositoryProvider).patchOrder(
            live.orderId!,
            deliveryAddress: address,
          );
    } catch (e) {
      if (_disposed) return;
      _append('update delivery address failed: $e');
    }
  }

  Future<void> submitRating(int rating) async {
    final sessionId = state.sessionId;
    if (sessionId == null) return;

    state = state.copyWith(rating: rating);

    try {
      await _sessionRepo.submitRating(sessionId: sessionId, rating: rating);
      if (_disposed) return;
      state = state.copyWith(ratingSubmitted: true);
    } catch (e) {
      if (_disposed) return;
      _append('submit rating failed: $e');
    }
  }

  Future<void> submitReview(String review) async {
    final sessionId = state.sessionId;
    if (sessionId == null || review.trim().isEmpty) return;

    try {
      await _sessionRepo.submitReview(sessionId: sessionId, review: review.trim());
      if (_disposed) return;
      state = state.copyWith(reviewSubmitted: true);
    } catch (e) {
      if (_disposed) return;
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

  /// Configure iOS audio session for playback + recording through the speaker
  /// with hardware echo cancellation (voiceChat mode).
  /// Must be called AFTER flutter_pcm_sound.setup() to override its config.
  Future<void> _configureIosAudioSession() async {
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

  void _append(String line) {
    final next = [...state.logs, line];
    final capped = next.length > 200 ? next.sublist(next.length - 200) : next;
    state = state.copyWith(logs: capped);
  }
}
