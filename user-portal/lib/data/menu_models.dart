class MenuItemVariant {
  final String id;
  final String name;
  final double price;
  final bool availability;
  final bool isDefault;

  const MenuItemVariant({
    required this.id,
    required this.name,
    required this.price,
    required this.availability,
    required this.isDefault,
  });

  factory MenuItemVariant.fromJson(Map<String, dynamic> json) {
    return MenuItemVariant(
      id: json['id'] as String,
      name: json['name'] as String,
      price: MenuItemOut._toDouble(json['price']),
      availability: json['availability'] as bool? ?? true,
      isDefault: json['is_default'] as bool? ?? false,
    );
  }
}

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
  final List<MenuItemVariant> variants;

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
    this.variants = const [],
  });

  factory MenuItemOut.fromJson(Map<String, dynamic> json) {
    final rawVariants = json['variants'] as List<dynamic>?;
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
      variants: rawVariants == null
          ? const []
          : rawVariants
              .map((e) => MenuItemVariant.fromJson(e as Map<String, dynamic>))
              .toList(),
    );
  }

  static double _toDouble(dynamic v) {
    if (v is num) return v.toDouble();
    if (v is String) return double.parse(v);
    return 0;
  }
}
