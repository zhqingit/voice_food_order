import 'package:web_socket_channel/web_socket_channel.dart';

WebSocketChannel connectWithAuth({required Uri uri, required String accessToken}) {
  // Browsers cannot set arbitrary headers on WebSocket connections.
  // Our backend requires Authorization header, so voice WS is not supported on web for now.
  throw UnsupportedError('Voice WebSocket is not supported on web (Authorization header required).');
}
