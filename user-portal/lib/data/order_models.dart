class OrderOut {
  final String id;
  final String storeId;
  final String? userId;
  final String status;
  final String channel;
  final double subtotal;
  final double tax;
  final double total;
  final String? notes;
  final DateTime createdAt;

  const OrderOut({
    required this.id,
    required this.storeId,
    required this.userId,
    required this.status,
    required this.channel,
    required this.subtotal,
    required this.tax,
    required this.total,
    required this.notes,
    required this.createdAt,
  });

  factory OrderOut.fromJson(Map<String, dynamic> json) {
    return OrderOut(
      id: json['id'] as String,
      storeId: json['store_id'] as String,
      userId: json['user_id'] as String?,
      status: json['status'] as String,
      channel: json['channel'] as String,
      subtotal: (json['subtotal'] as num).toDouble(),
      tax: (json['tax'] as num).toDouble(),
      total: (json['total'] as num).toDouble(),
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class OrderItemOut {
  final String id;
  final String orderId;
  final String menuItemId;
  final String? name;
  final int quantity;
  final double priceSnapshot;

  const OrderItemOut({
    required this.id,
    required this.orderId,
    required this.menuItemId,
    required this.name,
    required this.quantity,
    required this.priceSnapshot,
  });

  factory OrderItemOut.fromJson(Map<String, dynamic> json) {
    return OrderItemOut(
      id: json['id'] as String,
      orderId: json['order_id'] as String,
      menuItemId: json['menu_item_id'] as String,
      name: json['name'] as String?,
      quantity: json['quantity'] as int,
      priceSnapshot: (json['price_snapshot'] as num).toDouble(),
    );
  }
}
