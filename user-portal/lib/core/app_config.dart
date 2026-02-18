class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Host header required by the backend's host-based API partitioning.
  static const String apiHostHeader = 'user-api.local';
}
