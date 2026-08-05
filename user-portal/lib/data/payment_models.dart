/// Response from POST /voice/orders/{id}/payment-intent.
///
/// When [paymentAvailable] is false the store isn't payment-ready and the
/// client should present a "pay at store" message instead of charging.
class PaymentIntentResult {
  final bool paymentAvailable;
  final String? clientSecret;
  final String? publishableKey;
  final int amount; // order total in cents
  final String currency;
  final String? reason; // why payment is unavailable, when applicable

  const PaymentIntentResult({
    required this.paymentAvailable,
    required this.clientSecret,
    required this.publishableKey,
    required this.amount,
    required this.currency,
    required this.reason,
  });

  factory PaymentIntentResult.fromJson(Map<String, dynamic> json) {
    return PaymentIntentResult(
      paymentAvailable: json['payment_available'] as bool? ?? false,
      clientSecret: json['client_secret'] as String?,
      publishableKey: json['publishable_key'] as String?,
      amount: json['amount'] as int? ?? 0,
      currency: json['currency'] as String? ?? 'usd',
      reason: json['reason'] as String?,
    );
  }
}
