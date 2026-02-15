import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'voice_ws_channel.dart';

class VoiceWsClient {
  WebSocketChannel? _channel;
  StreamSubscription? _sub;

  final _events = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get events => _events.stream;

  bool get isConnected => _channel != null;

  Future<void> connect({required String storeId, String? orderId, required String accessToken}) async {
    if (_channel != null) return;

    final channel = connectVoiceWs(storeId: storeId, orderId: orderId, accessToken: accessToken);
    _channel = channel;

    _sub = channel.stream.listen(
      (data) {
        // pipecat transport may emit audio frames (binary) + json events.
        if (data is String) {
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

        // Binary/audio payloads: just surface a small marker for now.
        _events.add({'type': 'binary', 'bytes': (data as dynamic).length ?? 0});
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
  }
}
