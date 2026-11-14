import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_stripe/flutter_stripe.dart';

import '../../app/providers.dart';
import '../../core/api_error.dart';
import '../../core/app_config.dart';
import '../../data/payment_models.dart';
import '../../data/payment_repository.dart';

final paymentRepositoryProvider = Provider<PaymentRepository>((ref) {
  return PaymentRepository(ref.watch(apiClientProvider).dio);
});

enum PayOutcome {
  /// The charge went through (or the order was already paid).
  paid,

  /// The store doesn't take online payment: the customer pays at pickup/delivery.
  payAtStore,

  /// The customer closed the payment sheet.
  canceled,
}

/// A payment that failed; [message] is Stripe's text when it has one.
class PaymentFailure implements Exception {
  final String? message;
  const PaymentFailure([this.message]);
}

/// Runs the Stripe PaymentSheet for an order. Used right after a voice order
/// and from My Orders, so an order can be paid later.
Future<PayOutcome> payForOrder(WidgetRef ref, {required String orderId, required String storeName}) async {
  final PaymentIntentResult result;
  try {
    result = await ref.read(paymentRepositoryProvider).createPaymentIntent(orderId);
  } on DioException catch (e) {
    final error = e.error;
    if (error is ApiException && error.error.code == 'already_paid') return PayOutcome.paid;
    throw const PaymentFailure();
  }

  if (!result.paymentAvailable || result.clientSecret == null) return PayOutcome.payAtStore;
  final pk = result.publishableKey;
  if (pk == null || pk.isEmpty) throw const PaymentFailure();

  Stripe.publishableKey = pk;
  Stripe.merchantIdentifier = AppConfig.stripeMerchantIdentifier;
  await Stripe.instance.applySettings();

  try {
    await Stripe.instance.initPaymentSheet(
      paymentSheetParameters: SetupPaymentSheetParameters(
        paymentIntentClientSecret: result.clientSecret!,
        merchantDisplayName: storeName,
        applePay: const PaymentSheetApplePay(merchantCountryCode: 'US'),
        // testEnv: true pairs with Stripe test keys; set false for live.
        googlePay: const PaymentSheetGooglePay(merchantCountryCode: 'US', testEnv: true),
      ),
    );
    // Completes without throwing → the PaymentIntent succeeded. The backend
    // webhook marks the order paid.
    await Stripe.instance.presentPaymentSheet();
    return PayOutcome.paid;
  } on StripeException catch (e) {
    if (e.error.code == FailureCode.Canceled) return PayOutcome.canceled;
    throw PaymentFailure(e.error.localizedMessage);
  }
}
