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

  /// Check if a store is still published. Returns the store on success.
  /// Throws DioException with 410 if unpublished, 404 if not found.
  Future<StorePublicOut> getStore(String storeId) async {
    final res = await _dio.get<Map<String, dynamic>>('/user/stores/$storeId');
    return StorePublicOut.fromJson(res.data!);
  }
}
