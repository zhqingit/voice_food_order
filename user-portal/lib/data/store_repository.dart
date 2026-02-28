import 'package:dio/dio.dart';

import 'store_models.dart';

class StoreRepository {
  final Dio _dio;

  StoreRepository(this._dio);

  Future<List<StorePublicOut>> listStores() async {
    final res = await _dio.get<List<dynamic>>('/user/stores');
    final data = res.data;
    if (data == null) return [];
    return data
        .map((e) => StorePublicOut.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
