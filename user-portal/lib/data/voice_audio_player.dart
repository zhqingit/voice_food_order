import 'dart:async';
import 'dart:collection';
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';

/// Plays WAV audio chunks received from the backend TTS pipeline.
///
/// Chunks are queued and played sequentially to avoid overlapping audio.
class VoiceAudioPlayer {
  final AudioPlayer _player = AudioPlayer();
  final Queue<Uint8List> _queue = Queue<Uint8List>();
  bool _playing = false;
  bool _disposed = false;

  VoiceAudioPlayer() {
    _player.onPlayerComplete.listen((_) {
      _playing = false;
      _playNext();
    });
  }

  /// Enqueue a WAV audio chunk for playback.
  void enqueue(Uint8List wavBytes) {
    if (_disposed) return;
    _queue.add(wavBytes);
    _playNext();
  }

  void _playNext() {
    if (_disposed || _playing || _queue.isEmpty) return;
    _playing = true;
    final bytes = _queue.removeFirst();
    _player.play(BytesSource(bytes)).catchError((_) {
      _playing = false;
      _playNext();
    });
  }

  /// Stop current playback and clear the queue.
  Future<void> stop() async {
    _queue.clear();
    _playing = false;
    await _player.stop();
  }

  Future<void> dispose() async {
    _disposed = true;
    _queue.clear();
    _playing = false;
    await _player.dispose();
  }
}
