class ApiError {
  final int statusCode;
  final String code;
  final String detail;

  const ApiError({required this.statusCode, required this.code, required this.detail});

  factory ApiError.fromJson(int statusCode, Map<String, dynamic> json) {
    final code = (json['code'] as String?) ?? 'unknown_error';
    final detail = (json['detail'] as String?) ?? 'Unknown error';
    return ApiError(statusCode: statusCode, code: code, detail: detail);
  }
}

class ApiException implements Exception {
  final ApiError error;
  const ApiException(this.error);

  @override
  String toString() => 'ApiException(${error.statusCode}, ${error.code}): ${error.detail}';
}
