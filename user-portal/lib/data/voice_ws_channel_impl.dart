import 'package:web_socket_channel/web_socket_channel.dart';

WebSocketChannel connectWithAuth({required Uri uri, required String accessToken}) {
  throw UnsupportedError('WebSocket auth transport not configured for this platform');
}
