class StorePublicOut {
  final String id;
  final String name;
  final String? phone;
  final String? addressLine1;
  final String? city;
  final String? state;
  final String? country;
  final bool allowPickup;
  final bool allowDelivery;
  final String? minOrderAmount;

  const StorePublicOut({
    required this.id,
    required this.name,
    this.phone,
    this.addressLine1,
    this.city,
    this.state,
    this.country,
    required this.allowPickup,
    required this.allowDelivery,
    this.minOrderAmount,
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
    );
  }

  /// Returns a short location string, e.g. "San Francisco, CA"
  String? get locationLabel {
    if (city != null && state != null) return '$city, $state';
    if (city != null) return city;
    if (state != null) return state;
    return null;
  }
}
