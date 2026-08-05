import 'dart:async';
import 'dart:io' show Platform;
import 'dart:typed_data';

import 'package:flutter/services.dart';

import 'voice_audio_player.dart';
import 'voice_audio_recorder.dart';

/// Unified audio bridge for simultaneous recording + playback.
///
/// On iOS: uses a single AVAudioEngine via a native platform channel.
/// On Android: delegates to the existing [VoiceAudioPlayer] + [VoiceAudioRecorder].
class VoiceAudioBridge {
  // ── iOS native channels ──
  static const _method = MethodChannel('com.restoai.voice/audio_bridge');
  static const _event = EventChannel('com.restoai.voice/audio_bridge/recorded');

  // ── Android delegates ──
  VoiceAudioPlayer? _player;
  VoiceAudioRecorder? _recorder;

  // ── Callbacks ──
  void Function(Uint8List chunk)? onRecordedChunk;
  void Function(Object error)? onRecordError;

  /// Called when playback state changes (Android only — iOS uses hardware echo
  /// cancellation so the mic never needs to be paused).
  void Function(bool playing)? onPlayingChanged;

  StreamSubscription? _eventSub;
  bool _running = false;

  bool get isRunning => _running;

  /// Whether the bot is currently producing playback audio. Android only —
  /// iOS playback is native (not routed through [VoiceAudioPlayer]), so this
  /// returns false there.
  bool get isPlaying => _player?.isPlaying ?? false;

  /// Start recording + playback engine.
  ///
  /// On iOS the caller must configure the AVAudioSession (via the
  /// `audio_session` package) BEFORE calling this method.
  ///
  /// Returns `false` if microphone permission was not granted.
  Future<bool> startSession() async {
    if (_running) return true;

    if (Platform.isIOS) {
      return _startIos();
    } else {
      return _startAndroid();
    }
  }

  /// Feed a raw PCM16 24 kHz mono chunk for playback.
  void feedAudio(Uint8List pcm16Bytes) {
    if (!_running || pcm16Bytes.isEmpty) return;

    if (Platform.isIOS) {
      _method.invokeMethod('feedAudio', pcm16Bytes);
    } else {
      _player?.enqueue(pcm16Bytes);
    }
  }

  /// Flush all buffered playback audio (used for user interruption / barge-in).
  Future<void> clearPlayback() async {
    if (!_running) return;

    if (Platform.isIOS) {
      await _method.invokeMethod('clearPlayback');
    } else {
      await _player?.clearBuffer();
    }
  }

  /// Stop both recording and playback.
  Future<void> stopSession() async {
    if (!_running) return;
    _running = false;

    if (Platform.isIOS) {
      await _stopIos();
    } else {
      await _stopAndroid();
    }
  }

  Future<void> dispose() async {
    await stopSession();
    _player = null;
    _recorder = null;
  }

  // ── iOS implementation ──────────────────────────────────────────────────

  Future<bool> _startIos() async {
    // Listen for recorded audio chunks from native.
    _eventSub = _event.receiveBroadcastStream().listen((data) {
      if (data is Uint8List) {
        onRecordedChunk?.call(data);
      }
    }, onError: (e) {
      onRecordError?.call(e);
    });

    try {
      final ok = await _method.invokeMethod<bool>('startSession');
      if (ok != true) {
        await _eventSub?.cancel();
        _eventSub = null;
        return false;
      }
      _running = true;
      return true;
    } catch (e) {
      await _eventSub?.cancel();
      _eventSub = null;
      return false;
    }
  }

  Future<void> _stopIos() async {
    await _eventSub?.cancel();
    _eventSub = null;
    try {
      await _method.invokeMethod('stopSession');
    } catch (_) {}
  }

  // ── Android implementation ──────────────────────────────────────────────

  Future<bool> _startAndroid() async {
    final player = _player ??= VoiceAudioPlayer();
    final recorder = _recorder ??= VoiceAudioRecorder();

    await player.setup();

    // Mute mic while bot speaks to prevent echo feedback on Android.
    player.onPlayingChanged = (playing) {
      if (playing) {
        recorder.pause();
      } else {
        recorder.resume();
      }
      onPlayingChanged?.call(playing);
    };

    final granted = await recorder.start(
      onChunk: (chunk) => onRecordedChunk?.call(chunk),
      onError: (e) => onRecordError?.call(e),
    );

    if (!granted) return false;
    _running = true;
    return true;
  }

  Future<void> _stopAndroid() async {
    try {
      final player = _player;
      if (player != null) {
        player.onPlayingChanged = null;
        await player.stop();
      }
    } catch (_) {}

    try {
      await _recorder?.stop();
    } catch (_) {}
  }
}
