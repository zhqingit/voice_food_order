import 'package:dio/dio.dart';

import 'order_models.dart';

class OrderRepository {
  final Dio _dio;

  OrderRepository(this._dio);

  Future<OrderOut> getOrder(String orderId) async {
    final res = await _dio.get<Map<String, dynamic>>('/voice/orders/$orderId');
    final json = res.data;
    if (json == null) throw Exception('Empty response');
    return OrderOut.fromJson(json);
  }

  Future<List<OrderItemOut>> getOrderItems(String orderId) async {
    final res = await _dio.get<List<dynamic>>('/voice/orders/$orderId/items');
    final json = res.data;
    if (json == null) throw Exception('Empty response');
    return json.map((e) => OrderItemOut.fromJson(e as Map<String, dynamic>)).toList();
  }
}
