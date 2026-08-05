import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_pcm_sound/flutter_pcm_sound.dart';

/// Plays raw PCM16 audio chunks received from the backend voice pipeline.
///
/// Uses [FlutterPcmSound] for gap-free streaming: a single native AudioTrack
/// receives continuous PCM data — no WAV wrapping, no MediaPlayer restarts.
class VoiceAudioPlayer {
  static const int sampleRate = 24000;
  static const int numChannels = 1;

  /// How long the buffer must stay empty before we declare playback stopped.
  /// Keep short so the mic unmutes quickly after bot finishes speaking.
  static const Duration _drainDebounce = Duration(milliseconds: 150);

  bool _playing = false;
  bool _setup = false;
  bool _disposed = false;
  Timer? _drainTimer;

  /// Called when playback state changes (true = bot speaking, false = silent).
  /// Used by the controller to mute/unmute the mic.
  void Function(bool playing)? onPlayingChanged;

  /// Must be called once before [enqueue]. Sets up the native audio track.
  Future<void> setup() async {
    if (_setup) return;
    _setup = true;
    FlutterPcmSound.setFeedThreshold(2000);
    FlutterPcmSound.setFeedCallback(_onFeed);
    await FlutterPcmSound.setLogLevel(LogLevel.none);
    await FlutterPcmSound.setup(
      sampleRate: sampleRate,
      channelCount: numChannels,
      iosAudioCategory: IosAudioCategory.playAndRecord,
    );
  }

  /// Feed a raw PCM16 chunk (no WAV header) directly to the native audio track.
  void enqueue(Uint8List pcmBytes) {
    if (_disposed || !_setup || pcmBytes.isEmpty) return;

    // New audio arrived — cancel any pending "stopped" signal.
    _drainTimer?.cancel();
    _drainTimer = null;

    final samples = Int16List.view(
      pcmBytes.buffer,
      pcmBytes.offsetInBytes,
      pcmBytes.lengthInBytes ~/ 2,
    );
    // feed() is async; it can race a concurrent teardown (e.g. the session
    // auto-ends on order submit while the bot is still speaking). After
    // release() the native track is gone and feed throws "must call setup
    // first". Swallow that specific teardown race so it isn't an unhandled
    // async exception.
    FlutterPcmSound.feed(PcmArrayInt16.fromList(samples)).catchError((_) {});

    if (!_playing) {
      _playing = true;
      onPlayingChanged?.call(true);
    }
  }

  /// Callback from native side when buffered frames drop below threshold.
  void _onFeed(int remainingFrames) {
    if (remainingFrames == 0 && _playing) {
      // Buffer drained — but more chunks may arrive shortly.
      // Start a debounce timer; only declare "stopped" if no new audio
      // arrives within _drainDebounce.
      _drainTimer ??= Timer(_drainDebounce, () {
        _drainTimer = null;
        if (_playing) {
          _playing = false;
          onPlayingChanged?.call(false);
        }
      });
    }
  }

  bool get isPlaying => _playing;

  /// Flush any buffered audio immediately (used for barge-in / interruption).
  /// Tears down and re-creates the native audio track.
  Future<void> clearBuffer() async {
    if (!_setup || _disposed) return;
    _drainTimer?.cancel();
    _drainTimer = null;
    final wasPlaying = _playing;
    _playing = false;
    await FlutterPcmSound.release();
    _setup = false;
    await setup();
    if (wasPlaying) {
      onPlayingChanged?.call(false);
    }
  }

  Future<void> stop() async {
    if (!_setup) return;
    _drainTimer?.cancel();
    _drainTimer = null;
    _playing = false;
    await FlutterPcmSound.release();
    _setup = false;
    onPlayingChanged?.call(false);
  }

  Future<void> dispose() async {
    _disposed = true;
    _drainTimer?.cancel();
    _drainTimer = null;
    if (!_setup) return;
    _playing = false;
    await FlutterPcmSound.release();
    _setup = false;
  }
}
