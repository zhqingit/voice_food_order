import 'dart:async';
import 'dart:convert';
import 'dart:developer' as dev;
import 'dart:typed_data';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'voice_ws_channel.dart';

class VoiceWsClient {
  WebSocketChannel? _channel;
  StreamSubscription? _sub;

  final _events = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get events => _events.stream;

  final _audio = StreamController<Uint8List>.broadcast();
  Stream<Uint8List> get audioStream => _audio.stream;

  int _binaryMsgCount = 0;
  int _textMsgCount = 0;
  int _totalBinaryBytes = 0;

  bool get isConnected => _channel != null;

  Future<void> connect({required String storeId, String? orderId, String? sessionId, required String accessToken}) async {
    if (_channel != null) return;

    final channel = connectVoiceWs(storeId: storeId, orderId: orderId, sessionId: sessionId, accessToken: accessToken);
    _channel = channel;

    _binaryMsgCount = 0;
    _textMsgCount = 0;
    _totalBinaryBytes = 0;

    _sub = channel.stream.listen(
      (data) {
        // pipecat transport may emit audio frames (binary) + json events.
        if (data is String) {
          _textMsgCount++;
          dev.log('WS text #$_textMsgCount: ${data.substring(0, data.length.clamp(0, 80))}', name: 'VoiceWS');
          try {
            final decoded = jsonDecode(data);
            if (decoded is Map<String, dynamic>) {
              _events.add(decoded);
            } else {
              _events.add({'type': 'text', 'data': data});
            }
          } catch (_) {
            _events.add({'type': 'text', 'data': data});
          }
          return;
        }

        // Forward binary audio frames to the dedicated audio stream.
        if (data is List<int>) {
          _binaryMsgCount++;
          _totalBinaryBytes += data.length;
          if (_binaryMsgCount <= 3 || _binaryMsgCount % 50 == 0) {
            dev.log('WS binary #$_binaryMsgCount: ${data.length}B (total: ${_totalBinaryBytes}B, listeners: ${_audio.hasListener})', name: 'VoiceWS');
          }
          _audio.add(Uint8List.fromList(data));
        } else {
          dev.log('WS unknown data type: ${data.runtimeType}', name: 'VoiceWS');
        }
      },
      onError: (e) {
        _events.add({'type': 'error', 'error': e.toString()});
      },
      onDone: () {
        _events.add({'type': 'closed'});
      },
      cancelOnError: true,
    );
  }

  void sendJson(Map<String, dynamic> message) {
    final c = _channel;
    if (c == null) return;
    c.sink.add(jsonEncode(message));
  }

  void sendBytes(Uint8List bytes) {
    final c = _channel;
    if (c == null) return;
    c.sink.add(bytes);
  }

  Future<void> disconnect() async {
    final c = _channel;
    if (c == null) return;

    _channel = null;
    await _sub?.cancel();
    _sub = null;

    await c.sink.close();
  }

  Future<void> dispose() async {
    await disconnect();
    await _events.close();
    await _audio.close();
  }
}
