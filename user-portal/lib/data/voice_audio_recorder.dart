import 'dart:async';
import 'dart:typed_data';

import 'package:record/record.dart';

class VoiceAudioRecorder {
  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<Uint8List>? _sub;

  bool get isRecording => _sub != null;

  /// Starts streaming PCM16 mono @ 16kHz.
  ///
  /// Returns false if permission is not granted.
  Future<bool> start({required void Function(Uint8List chunk) onChunk}) async {
    if (_sub != null) return true;

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
      onChunk,
      onError: (_) {
        // Let caller handle; recorder may stop unexpectedly.
      },
      cancelOnError: true,
    );

    return true;
  }

  Future<void> stop() async {
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
