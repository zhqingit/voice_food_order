import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenBundle {
  final String accessToken;
  final String refreshToken;
  final String sessionId;

  const TokenBundle({required this.accessToken, required this.refreshToken, required this.sessionId});
}

class TokenStore {
  static const _kAccessToken = 'access_token';
  static const _kRefreshToken = 'refresh_token';
  static const _kSessionId = 'session_id';

  final FlutterSecureStorage _storage;

  TokenStore(this._storage);

  Future<TokenBundle?> read() async {
    final access = await _storage.read(key: _kAccessToken);
    final refresh = await _storage.read(key: _kRefreshToken);
    final sessionId = await _storage.read(key: _kSessionId);
    if (access == null || refresh == null || sessionId == null) return null;
    return TokenBundle(accessToken: access, refreshToken: refresh, sessionId: sessionId);
  }

  Future<void> write(TokenBundle bundle) async {
    await _storage.write(key: _kAccessToken, value: bundle.accessToken);
    await _storage.write(key: _kRefreshToken, value: bundle.refreshToken);
    await _storage.write(key: _kSessionId, value: bundle.sessionId);
  }

  Future<void> clear() async {
    await _storage.delete(key: _kAccessToken);
    await _storage.delete(key: _kRefreshToken);
    await _storage.delete(key: _kSessionId);
  }
}
