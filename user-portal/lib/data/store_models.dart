import '../core/app_config.dart';

class DayHours {
  final int dayOfWeek; // 0=Mon .. 6=Sun
  final String openTime; // "HH:MM"
  final String closeTime; // "HH:MM"
  final bool isClosed;

  const DayHours({
    required this.dayOfWeek,
    required this.openTime,
    required this.closeTime,
    required this.isClosed,
  });

  factory DayHours.fromJson(Map<String, dynamic> json) {
    return DayHours(
      dayOfWeek: json['day_of_week'] as int,
      openTime: json['open_time'] as String,
      closeTime: json['close_time'] as String,
      isClosed: (json['is_closed'] as bool?) ?? false,
    );
  }
}

class StorePublicOut {
  final String id;
  final String name;
  final String? phone;
  final String? addressLine1;
  final String? city;
  final String? state;
  final String? country;
  final String? timezone;
  final bool allowPickup;
  final bool allowDelivery;
  final String? minOrderAmount;
  final String? logoUrl;
  final List<DayHours> hours;

  const StorePublicOut({
    required this.id,
    required this.name,
    this.phone,
    this.addressLine1,
    this.city,
    this.state,
    this.country,
    this.timezone,
    required this.allowPickup,
    required this.allowDelivery,
    this.minOrderAmount,
    this.logoUrl,
    this.hours = const [],
  });

  factory StorePublicOut.fromJson(Map<String, dynamic> json) {
    return StorePublicOut(
      id: json['id'] as String,
      name: json['name'] as String,
      phone: json['phone'] as String?,
      addressLine1: json['address_line1'] as String?,
      city: json['city'] as String?,
      state: json['state'] as String?,
      country: json['country'] as String?,
      allowPickup: (json['allow_pickup'] as bool?) ?? true,
      allowDelivery: (json['allow_delivery'] as bool?) ?? true,
      minOrderAmount: json['min_order_amount']?.toString(),
      timezone: json['timezone'] as String?,
      logoUrl: json['logo_url'] != null
          ? '${AppConfig.apiBaseUrl}${json['logo_url']}'
          : null,
      hours: (json['hours'] as List<dynamic>?)
              ?.map((h) => DayHours.fromJson(h as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  /// Returns a short location string, e.g. "San Francisco, CA"
  String? get locationLabel {
    if (city != null && state != null) return '$city, $state';
    if (city != null) return city;
    if (state != null) return state;
    return null;
  }

  /// Check if the store is currently open based on its hours.
  /// Returns null if no hours are set (unknown status).
  bool? get isCurrentlyOpen {
    if (hours.isEmpty) return null;

    final now = DateTime.now();
    // DateTime weekday: 1=Mon .. 7=Sun → our model: 0=Mon .. 6=Sun
    final todayIndex = now.weekday - 1;

    final todayHours = hours.where((h) => h.dayOfWeek == todayIndex).toList();
    if (todayHours.isEmpty) return null;

    final day = todayHours.first;
    if (day.isClosed) return false;

    final openParts = day.openTime.split(':');
    final closeParts = day.closeTime.split(':');
    final openMinutes = int.parse(openParts[0]) * 60 + int.parse(openParts[1]);
    final closeMinutes = int.parse(closeParts[0]) * 60 + int.parse(closeParts[1]);
    final nowMinutes = now.hour * 60 + now.minute;

    return nowMinutes >= openMinutes && nowMinutes < closeMinutes;
  }

  /// Today's hours as a display string, e.g. "09:00 - 21:00" or "Closed"
  String? get todayHoursLabel {
    if (hours.isEmpty) return null;
    final todayIndex = DateTime.now().weekday - 1;
    final todayHours = hours.where((h) => h.dayOfWeek == todayIndex).toList();
    if (todayHours.isEmpty) return null;
    final day = todayHours.first;
    if (day.isClosed) return 'Closed';
    return '${day.openTime} - ${day.closeTime}';
  }
}
