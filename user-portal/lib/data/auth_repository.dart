import 'package:dio/dio.dart';

import '../core/token_store.dart';
import 'auth_models.dart';

class AuthRepository {
  final Dio _dio;

  AuthRepository(this._dio);

  Future<TokenBundle> signup({required String email, required String password}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/auth/signup',
      data: {'email': email, 'password': password},
    );
    return _bundleFromTokenResponse(TokenResponse.fromJson(res.data!));
  }

  Future<TokenBundle> login({required String email, required String password}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    return _bundleFromTokenResponse(TokenResponse.fromJson(res.data!));
  }

  Future<TokenBundle> refresh({required TokenBundle current}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/auth/refresh',
      data: {'refresh_token': current.refreshToken, 'session_id': current.sessionId},
    );
    return _bundleFromTokenResponse(TokenResponse.fromJson(res.data!));
  }

  Future<void> logoutCurrent({required String sessionId}) async {
    await _dio.post(
      '/auth/logout',
      data: {'scope': 'current', 'session_id': sessionId},
    );
  }

  Future<void> logoutAll() async {
    await _dio.post(
      '/auth/logout',
      data: {'scope': 'all'},
    );
  }

  Future<UserOut> me() async {
    final res = await _dio.get<Map<String, dynamic>>('/me');
    return UserOut.fromJson(res.data!);
  }
}

TokenBundle _bundleFromTokenResponse(TokenResponse tr) {
  return TokenBundle(accessToken: tr.accessToken, refreshToken: tr.refreshToken, sessionId: tr.sessionId);
}
