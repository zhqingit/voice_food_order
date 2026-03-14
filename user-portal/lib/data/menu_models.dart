class MenuItemOut {
  final String id;
  final String name;
  final String? category;
  final double price;
  final double? priceSmall;
  final double? priceMedium;
  final double? priceLarge;
  final String? description;
  final bool availability;

  const MenuItemOut({
    required this.id,
    required this.name,
    this.category,
    required this.price,
    this.priceSmall,
    this.priceMedium,
    this.priceLarge,
    this.description,
    required this.availability,
  });

  factory MenuItemOut.fromJson(Map<String, dynamic> json) {
    return MenuItemOut(
      id: json['id'] as String,
      name: json['name'] as String,
      category: json['category'] as String?,
      price: _toDouble(json['price']),
      priceSmall: json['price_small'] != null ? _toDouble(json['price_small']) : null,
      priceMedium: json['price_medium'] != null ? _toDouble(json['price_medium']) : null,
      priceLarge: json['price_large'] != null ? _toDouble(json['price_large']) : null,
      description: json['description'] as String?,
      availability: json['availability'] as bool? ?? true,
    );
  }

  static double _toDouble(dynamic v) {
    if (v is num) return v.toDouble();
    if (v is String) return double.parse(v);
    return 0;
  }
}
