import 'package:dio/dio.dart';

class VoiceSessionOut {
  final String id;
  final String storeId;
  final String userId;
  final String channel;
  final String status;
  final DateTime startedAt;
  final DateTime? endedAt;

  const VoiceSessionOut({
    required this.id,
    required this.storeId,
    required this.userId,
    required this.channel,
    required this.status,
    required this.startedAt,
    required this.endedAt,
  });

  factory VoiceSessionOut.fromJson(Map<String, dynamic> json) {
    return VoiceSessionOut(
      id: json['id'] as String,
      storeId: json['store_id'] as String,
      userId: json['user_id'] as String,
      channel: json['channel'] as String,
      status: (json['status'] as String?) ?? 'active',
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: (json['ended_at'] as String?) == null ? null : DateTime.parse(json['ended_at'] as String),
    );
  }
}

class VoiceSessionRepository {
  final Dio _dio;

  VoiceSessionRepository(this._dio);

  Future<VoiceSessionOut> create({required String storeId, String channel = 'voice'}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/voice/sessions',
      data: {
        'store_id': storeId,
        'channel': channel,
      },
    );

    final json = res.data;
    if (json == null) {
      throw Exception('Empty response');
    }
    return VoiceSessionOut.fromJson(json);
  }

  Future<VoiceSessionOut> end({required String sessionId}) async {
    final res = await _dio.post<Map<String, dynamic>>('/voice/sessions/$sessionId/end');
    final json = res.data;
    if (json == null) {
      throw Exception('Empty response');
    }
    return VoiceSessionOut.fromJson(json);
  }
}
