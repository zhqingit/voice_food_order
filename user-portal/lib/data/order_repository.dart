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

  Future<OrderOut> patchOrder(
    String orderId, {
    String? deliveryAddress,
    String? fulfillmentType,
    String? customerName,
  }) async {
    final body = <String, dynamic>{};
    if (deliveryAddress != null) body['delivery_address'] = deliveryAddress;
    if (fulfillmentType != null) body['fulfillment_type'] = fulfillmentType;
    if (customerName != null) body['customer_name'] = customerName;
    final res = await _dio.patch<Map<String, dynamic>>('/voice/orders/$orderId', data: body);
    final json = res.data;
    if (json == null) throw Exception('Empty response');
    return OrderOut.fromJson(json);
  }
}
