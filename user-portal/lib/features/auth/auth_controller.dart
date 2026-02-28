import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

import '../../app/providers.dart';
import '../../core/api_error.dart';

sealed class AuthState {
  const AuthState();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class Unauthenticated extends AuthState {
  final String? message;
  const Unauthenticated({this.message});
}

class Authenticated extends AuthState {
  const Authenticated();
}

class Guest extends AuthState {
  const Guest();
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(AuthController.new);

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() {
    // Kick off restore after first build.
    _restore();
    return const AuthLoading();
  }

  Future<void> _restore() async {
    final tokenStore = ref.read(tokenStoreProvider);
    final repo = ref.read(authRepositoryProvider);

    final bundle = await tokenStore.read();
    if (bundle == null) {
      state = const Unauthenticated();
      return;
    }

    // If access token still valid, we can treat user as signed-in immediately.
    final accessExpired = _isJwtExpiredSafe(bundle.accessToken);
    if (!accessExpired) {
      state = const Authenticated();
      return;
    }

    // Access expired: try refresh (if online).
    if (!await _isOnline()) {
      state = const Unauthenticated(message: 'Offline: cannot restore session.');
      return;
    }

    try {
      final refreshed = await repo.refresh(current: bundle);
      await tokenStore.write(refreshed);
      state = const Authenticated();
    } catch (e) {
      // If refresh fails, clear local tokens and require login.
      await tokenStore.clear();
      state = Unauthenticated(message: _messageFromError(e));
    }
  }

  Future<void> login(String email, String password) async {
    state = const AuthLoading();
    final repo = ref.read(authRepositoryProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    try {
      final bundle = await repo.login(email: email, password: password);
      await tokenStore.write(bundle);
      state = const Authenticated();
    } catch (e) {
      state = Unauthenticated(message: _messageFromError(e));
    }
  }

  Future<void> signup(String email, String password) async {
    state = const AuthLoading();
    final repo = ref.read(authRepositoryProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    try {
      final bundle = await repo.signup(email: email, password: password);
      await tokenStore.write(bundle);
      state = const Authenticated();
    } catch (e) {
      state = Unauthenticated(message: _messageFromError(e));
    }
  }

  Future<void> continueAsGuest() async {
    state = const AuthLoading();
    final repo = ref.read(authRepositoryProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    try {
      final bundle = await repo.guestLogin();
      await tokenStore.write(bundle);
      state = const Authenticated();
    } catch (e) {
      state = Unauthenticated(message: _messageFromError(e));
    }
  }

  Future<void> logoutCurrent() async {
    final repo = ref.read(authRepositoryProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    final bundle = await tokenStore.read();
    try {
      if (bundle != null) {
        await repo.logoutCurrent(sessionId: bundle.sessionId);
      }
    } finally {
      await tokenStore.clear();
      state = const Unauthenticated();
    }
  }

  Future<void> logoutAll() async {
    final repo = ref.read(authRepositoryProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    try {
      await repo.logoutAll();
    } finally {
      await tokenStore.clear();
      state = const Unauthenticated();
    }
  }

  /// Called on app resume or before protected calls.
  Future<void> refreshIfNeeded({Duration leeway = const Duration(seconds: 30)}) async {
    if (state is! Authenticated) return;

    final tokenStore = ref.read(tokenStoreProvider);
    final repo = ref.read(authRepositoryProvider);

    final bundle = await tokenStore.read();
    if (bundle == null) {
      state = const Unauthenticated();
      return;
    }

    final remaining = _jwtRemaining(bundle.accessToken);
    if (remaining != null && remaining > leeway) return;

    if (!await _isOnline()) return;

    try {
      final refreshed = await repo.refresh(current: bundle);
      await tokenStore.write(refreshed);
      state = const Authenticated();
    } catch (e) {
      // If refresh failed due to bad network, keep signed-in state.
      if (_isNetworkError(e)) return;

      await tokenStore.clear();
      state = Unauthenticated(message: _messageFromError(e));
    }
  }
}

String _messageFromError(Object e) {
  if (e is DioException && e.error is ApiException) {
    return (e.error as ApiException).error.detail;
  }
  if (e is ApiException) return e.error.detail;
  return 'Request failed';
}

bool _isNetworkError(Object e) {
  if (e is DioException && e.error is ApiException) {
    return (e.error as ApiException).error.code == 'network_error';
  }
  if (e is ApiException) return e.error.code == 'network_error';
  return false;
}

bool _isJwtExpiredSafe(String token) {
  try {
    return JwtDecoder.isExpired(token);
  } catch (_) {
    return true;
  }
}

Duration? _jwtRemaining(String token) {
  try {
    final exp = JwtDecoder.getExpirationDate(token);
    return exp.difference(DateTime.now());
  } catch (_) {
    return null;
  }
}

Future<bool> _isOnline() async {
  final result = await Connectivity().checkConnectivity();
  return result.contains(ConnectivityResult.mobile) ||
      result.contains(ConnectivityResult.wifi) ||
      result.contains(ConnectivityResult.ethernet) ||
      result.contains(ConnectivityResult.vpn);
}
