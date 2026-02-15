import 'dart:async';

import 'package:dio/dio.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

import '../core/api_error.dart';
import '../core/app_config.dart';
import '../core/token_store.dart';

class ApiClient {
  final Dio dio;

  ApiClient._(this.dio);

  static ApiClient create({required TokenStore tokenStore}) {
    final dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
        sendTimeout: const Duration(seconds: 10),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    final refreshCoordinator = _RefreshCoordinator(dio: dio, tokenStore: tokenStore);

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final skipAuth = options.extra['skipAuth'] == true;
          if (!skipAuth) {
            final bundle = await tokenStore.read();
            if (bundle != null) {
              options.headers['Authorization'] = 'Bearer ${bundle.accessToken}';
            }
          }
          handler.next(options);
        },
        onError: (err, handler) async {
          final response = err.response;
          final status = response?.statusCode;

          // Only attempt refresh on 401 from protected endpoints.
          if (status == 401 && !_isAuthEndpoint(err.requestOptions.path)) {
            final bundle = await tokenStore.read();
            if (bundle == null) return handler.next(err);

            // If the access token isn't expired yet, don't refresh; just surface the error.
            // (Covers clock skew / backend invalidation cases.)
            final isExpired = JwtDecoder.isExpired(bundle.accessToken);
            if (!isExpired) return handler.next(err);

            try {
              final newBundle = await refreshCoordinator.refresh(bundle);
              await tokenStore.write(newBundle);

              final retryResponse = await dio.fetch<dynamic>(
                err.requestOptions.copyWith(
                  headers: Map<String, dynamic>.from(err.requestOptions.headers)
                    ..['Authorization'] = 'Bearer ${newBundle.accessToken}',
                ),
              );
              return handler.resolve(retryResponse);
            } catch (_) {
              // Refresh failed; let caller handle (usually sign-out).
              return handler.next(err);
            }
          }

          handler.next(err);
        },
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onError: (err, handler) {
          final res = err.response;
          final statusCode = res?.statusCode ?? 0;
          final data = res?.data;

          if (data is Map<String, dynamic> && data.containsKey('code') && data.containsKey('detail')) {
            return handler.reject(
              DioException(
                requestOptions: err.requestOptions,
                response: err.response,
                type: err.type,
                error: ApiException(ApiError.fromJson(statusCode, data)),
              ),
            );
          }

          if (err.type == DioExceptionType.connectionTimeout ||
              err.type == DioExceptionType.receiveTimeout ||
              err.type == DioExceptionType.sendTimeout ||
              err.type == DioExceptionType.connectionError) {
            return handler.reject(
              DioException(
                requestOptions: err.requestOptions,
                response: err.response,
                type: err.type,
                error: const ApiException(ApiError(statusCode: 0, code: 'network_error', detail: 'Network error')),
              ),
            );
          }

          handler.next(err);
        },
      ),
    );

    return ApiClient._(dio);
  }
}

bool _isAuthEndpoint(String path) {
  // Backend user auth routes are under /user/auth
  return path.contains('/user/auth/');
}

class _RefreshCoordinator {
  final Dio dio;
  final TokenStore tokenStore;

  Future<TokenBundle>? _inFlight;

  _RefreshCoordinator({required this.dio, required this.tokenStore});

  Future<TokenBundle> refresh(TokenBundle current) {
    final existing = _inFlight;
    if (existing != null) return existing;

    final future = _doRefresh(current);
    _inFlight = future;
    future.whenComplete(() => _inFlight = null);
    return future;
  }

  Future<TokenBundle> _doRefresh(TokenBundle current) async {
    final res = await dio.post<Map<String, dynamic>>(
      '/user/auth/refresh',
      data: {
        'refresh_token': current.refreshToken,
        'session_id': current.sessionId,
      },
      options: Options(extra: {'skipAuth': true}),
    );

    final json = res.data;
    if (json == null) {
      throw const ApiException(ApiError(statusCode: 0, code: 'bad_response', detail: 'Empty response'));
    }

    return TokenBundle(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      sessionId: json['session_id'] as String,
    );
  }
}
