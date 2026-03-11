import 'dart:async';
import 'dart:typed_data';

import 'package:record/record.dart';

class VoiceAudioRecorder {
  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<Uint8List>? _sub;
  bool _paused = false;

  bool get isRecording => _sub != null;
  bool get isPaused => _paused;

  /// Pause sending audio chunks (drops them silently).
  /// The platform recorder keeps running to avoid permission re-requests.
  void pause() => _paused = true;

  /// Resume sending audio chunks after a pause.
  void resume() => _paused = false;

  /// Starts streaming PCM16 mono @ 16kHz.
  ///
  /// Returns false if permission is not granted.
  /// [onChunk] receives audio when not paused (sent to server).
  /// [onError] is called if the recorder stops unexpectedly.
  Future<bool> start({
    required void Function(Uint8List chunk) onChunk,
    void Function(Object error)? onError,
  }) async {
    if (_sub != null) return true;
    _paused = false;

    final ok = await _recorder.hasPermission();
    if (!ok) return false;

    final stream = await _recorder.startStream(
      const RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        sampleRate: 16000,
        numChannels: 1,
      ),
    );

    _sub = stream.listen(
      (chunk) {
        if (!_paused) {
          onChunk(chunk);
        }
      },
      onError: (e) {
        onError?.call(e);
      },
      cancelOnError: true,
    );

    return true;
  }

  Future<void> stop() async {
    _paused = false;
    final sub = _sub;
    _sub = null;
    await sub?.cancel();
    await _recorder.stop();
  }

  Future<void> dispose() async {
    await stop();
    await _recorder.dispose();
  }
}
