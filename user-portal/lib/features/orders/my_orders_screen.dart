import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../data/order_models.dart';
import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../voice/voice_controller.dart';
import 'pay_for_order.dart';

const _kOrange = Color(0xFFFF8A2A);
const _kOrangeEnd = Color(0xFFFFB15A);
const _kTextDark = Color(0xFF2E241A);
const _kTextMuted = Color(0xFF6D5D4B);
const _kCardBg = Color(0xFFFFFBF5);
const _kGreen = Color(0xFF2E7D32);
const _kAmber = Color(0xFFB25E00);

/// The signed-in customer's placed orders, newest first.
final myOrdersProvider = FutureProvider.autoDispose<List<OrderOut>>((ref) {
  return ref.watch(orderRepositoryProvider).listMyOrders();
});

final _orderItemsProvider = FutureProvider.autoDispose.family<List<OrderItemOut>, String>((ref, orderId) {
  return ref.watch(orderRepositoryProvider).getOrderItems(orderId);
});

String _money(double amount) => '\$${amount.toStringAsFixed(2)}';

String _statusLabel(AppLocalizations l10n, String status) => switch (status) {
      'submitted' => l10n.statusSubmitted,
      'confirmed' => l10n.statusConfirmed,
      'preparing' => l10n.statusPreparing,
      'ready' => l10n.statusReady,
      'completed' => l10n.statusCompleted,
      'cancelled' => l10n.statusCancelled,
      _ => status,
    };

class MyOrdersScreen extends ConsumerWidget {
  const MyOrdersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final orders = ref.watch(myOrdersProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          bottom: false,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_rounded, color: _kTextDark),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    Text(l10n.myOrders, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: _kTextDark)),
                  ],
                ),
              ),
              Expanded(
                child: RefreshIndicator(
                  color: _kOrange,
                  onRefresh: () => ref.refresh(myOrdersProvider.future),
                  child: orders.when(
                    loading: () => const Center(child: CircularProgressIndicator(color: _kOrange)),
                    error: (_, __) => _Message(
                      text: l10n.somethingWentWrong,
                      action: TextButton(onPressed: () => ref.invalidate(myOrdersProvider), child: Text(l10n.tryAgain)),
                    ),
                    data: (list) => list.isEmpty
                        ? _Message(text: l10n.noOrdersYet)
                        : ListView.separated(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                            itemCount: list.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 12),
                            itemBuilder: (_, i) => _OrderCard(order: list[i]),
                          ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  final String text;
  final Widget? action;

  const _Message({required this.text, this.action});

  @override
  Widget build(BuildContext context) {
    // Scrollable so pull-to-refresh still works on an empty list.
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 120),
        Center(child: Text(text, style: const TextStyle(fontSize: 16, color: _kTextMuted))),
        if (action != null) Center(child: action),
      ],
    );
  }
}

class _OrderCard extends ConsumerStatefulWidget {
  final OrderOut order;

  const _OrderCard({required this.order});

  @override
  ConsumerState<_OrderCard> createState() => _OrderCardState();
}

class _OrderCardState extends ConsumerState<_OrderCard> {
  bool _expanded = false;
  bool _busy = false;
  bool _paidHere = false; // the webhook may lag the payment sheet by a moment

  OrderOut get _order => widget.order;
  bool get _paid => _order.paymentStatus == 'paid' || _paidHere;

  Future<void> _pay() async {
    final l10n = AppLocalizations.of(context)!;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      final outcome = await payForOrder(ref, orderId: _order.id, storeName: _order.storeName ?? '');
      if (!mounted) return;
      setState(() => _paidHere = outcome == PayOutcome.paid);
      if (outcome == PayOutcome.paid) ref.invalidate(myOrdersProvider);
      if (outcome == PayOutcome.payAtStore) messenger.showSnackBar(SnackBar(content: Text(l10n.payAtStoreNote)));
    } on PaymentFailure catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message ?? l10n.paymentFailed)));
    } catch (_) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.paymentFailed)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final placedAt = DateFormat.yMMMd().add_jm().format(_order.createdAt.toLocal());
    final open = !{'completed', 'cancelled'}.contains(_order.status);

    return Container(
      decoration: BoxDecoration(
        color: _kCardBg,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(color: _kTextMuted.withValues(alpha: 0.08), blurRadius: 14, offset: const Offset(0, 4))],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => setState(() => _expanded = !_expanded),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _order.storeName ?? '',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: _kTextDark),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(_money(_order.total), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: _kOrange)),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${l10n.orderNumber(_order.shortCode)} · $placedAt',
                  style: TextStyle(fontSize: 13, color: _kTextMuted.withValues(alpha: 0.85)),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _Chip(label: _statusLabel(l10n, _order.status), color: _kTextMuted),
                    if (_order.fulfillmentType != null)
                      _Chip(label: _order.fulfillmentType == 'delivery' ? l10n.delivery : l10n.pickup, color: _kTextMuted),
                    _Chip(label: _paid ? l10n.paid : l10n.unpaid, color: _paid ? _kGreen : _kAmber),
                  ],
                ),
                if (_expanded) _Items(orderId: _order.id),
                if (!_paid && _order.canPayOnline) ...[
                  const SizedBox(height: 14),
                  _PayButton(label: l10n.payAmount(_money(_order.total)), busy: _busy, onPressed: _pay),
                ] else if (!_paid && open) ...[
                  const SizedBox(height: 10),
                  Text(l10n.payAtStoreNote, style: const TextStyle(fontSize: 12, color: _kAmber)),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Items extends ConsumerWidget {
  final String orderId;

  const _Items({required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = ref.watch(_orderItemsProvider(orderId));
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: items.when(
        loading: () => const LinearProgressIndicator(color: _kOrange),
        error: (_, __) => Text(AppLocalizations.of(context)!.somethingWentWrong),
        data: (list) => Column(
          children: [
            for (final item in list)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${item.quantity}×  ', style: const TextStyle(fontWeight: FontWeight.w600, color: _kTextDark)),
                    Expanded(
                      child: Text(
                        [
                          item.name ?? '',
                          if (item.variantName != null) '(${item.variantName})',
                          if (item.note != null && item.note!.isNotEmpty) '— ${item.note}',
                        ].join(' '),
                        style: const TextStyle(color: _kTextDark),
                      ),
                    ),
                    Text(_money(item.priceSnapshot * item.quantity), style: const TextStyle(color: _kTextMuted)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final Color color;

  const _Chip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
      child: Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
    );
  }
}

class _PayButton extends StatelessWidget {
  final String label;
  final bool busy;
  final VoidCallback onPressed;

  const _PayButton({required this.label, required this.busy, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: busy ? null : onPressed,
      child: Container(
        width: double.infinity,
        height: 46,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          gradient: const LinearGradient(colors: [_kOrange, _kOrangeEnd]),
        ),
        child: Center(
          child: busy
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : Text(label, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
        ),
      ),
    );
  }
}
