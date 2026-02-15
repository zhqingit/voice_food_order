import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/app_config.dart';

import 'voice_ws_channel_impl.dart'
    if (dart.library.io) 'voice_ws_channel_io.dart'
    if (dart.library.html) 'voice_ws_channel_web.dart' as impl;

Uri buildVoiceWsUri({required String storeId, String? orderId}) {
  final http = Uri.parse(AppConfig.apiBaseUrl);
  final wsScheme = http.scheme == 'https' ? 'wss' : 'ws';

  return http.replace(
    scheme: wsScheme,
    path: '/voice/ws',
    queryParameters: {
      'store_id': storeId,
      if (orderId != null) 'order_id': orderId,
    },
  );
}

WebSocketChannel connectVoiceWs({required String storeId, String? orderId, required String accessToken}) {
  final uri = buildVoiceWsUri(storeId: storeId, orderId: orderId);
  return impl.connectWithAuth(uri: uri, accessToken: accessToken);
}
