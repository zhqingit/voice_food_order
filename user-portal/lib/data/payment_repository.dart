import 'package:dio/dio.dart';

import 'payment_models.dart';

class PaymentRepository {
  final Dio _dio;

  PaymentRepository(this._dio);

  Future<PaymentIntentResult> createPaymentIntent(String orderId) async {
    final res = await _dio.post<Map<String, dynamic>>('/voice/orders/$orderId/payment-intent');
    final json = res.data;
    if (json == null) throw Exception('Empty response');
    return PaymentIntentResult.fromJson(json);
  }
}
