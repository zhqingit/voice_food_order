import 'package:dio/dio.dart';

import 'menu_models.dart';

class MenuRepository {
  final Dio _dio;

  MenuRepository(this._dio);

  Future<List<MenuItemOut>> getStoreMenu(String storeId) async {
    final res = await _dio.get<List<dynamic>>('/user/stores/$storeId/menu');
    final data = res.data;
    if (data == null) return [];
    return data
        .map((e) => MenuItemOut.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
