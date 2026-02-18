import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/app_config.dart';

WebSocketChannel connectWithAuth({required Uri uri, required String accessToken}) {
  return IOWebSocketChannel.connect(
    uri,
    headers: {
      'Authorization': 'Bearer $accessToken',
      'Host': AppConfig.apiHostHeader,
    },
  );
}
