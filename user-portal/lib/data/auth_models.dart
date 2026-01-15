class TokenResponse {
  final String accessToken;
  final String refreshToken;
  final String sessionId;

  const TokenResponse({required this.accessToken, required this.refreshToken, required this.sessionId});

  factory TokenResponse.fromJson(Map<String, dynamic> json) {
    return TokenResponse(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      sessionId: json['session_id'] as String,
    );
  }
}

class UserOut {
  final String id;
  final String email;

  const UserOut({required this.id, required this.email});

  factory UserOut.fromJson(Map<String, dynamic> json) {
    return UserOut(
      id: json['id'] as String,
      email: json['email'] as String,
    );
  }
}
