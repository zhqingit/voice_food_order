class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    //defaultValue: 'http://localhost:8000',
    defaultValue: 'http://192.168.1.25:8000',
    //defaultValue: 'http://136.112.211.46:8000',
    //defaultValue: 'https://voxeats.rest-oai.com',
  );

  /// Host header required by the backend's host-based API partitioning.
  static const String apiHostHeader = 'user-api.local';

  /// Apple Pay merchant identifier (must match the Merchant ID configured in
  /// Xcode's Apple Pay capability). Android/Google Pay does not use this.
  static const String stripeMerchantIdentifier = 'merchant.com.voxeats';
}
