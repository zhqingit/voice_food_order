import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../../ui/style/app_stage.dart';
import '../settings/settings_screen.dart';
import 'voice_controller.dart';

class VoiceOrderScreen extends ConsumerWidget {
  final String storeName;
  final String storeId;

  const VoiceOrderScreen({super.key, required this.storeName, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final voice = ref.watch(voiceControllerProvider);

    final showPostSession = voice.sessionEnded && !voice.connected;

    return Scaffold(
      appBar: AppBar(
        title: Text(storeName),
        actions: [
          IconButton(
            tooltip: l10n?.settingsTitle ?? 'Settings',
            icon: const Icon(Icons.settings_outlined),
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
            },
          ),
        ],
      ),
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: showPostSession
                ? _PostSessionView(storeName: storeName, storeId: storeId)
                : _ActiveSessionView(storeName: storeName, storeId: storeId),
          ),
        ),
      ),
    );
  }
}

/// The normal voice-ordering view (connect / listening / waveform).
class _ActiveSessionView extends ConsumerWidget {
  final String storeName;
  final String storeId;

  const _ActiveSessionView({required this.storeName, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final voice = ref.watch(voiceControllerProvider);

    return LayoutBuilder(
      builder: (context, constraints) {
        final h = constraints.maxHeight;
        final orbSize = h < 600 ? 80.0 : 110.0;
        final waveW = (h * 0.35).clamp(180.0, 260.0);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // --- Header ---
            Text(
              l10n?.voiceTitle ?? 'Voice order',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            AppStage(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          storeName,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(999),
                          color: scheme.primary.withValues(alpha: 0.15),
                          border: Border.all(color: scheme.primary.withValues(alpha: 0.5)),
                        ),
                        child: Text(
                          voice.connected ? 'Listening' : 'Ready',
                          style: Theme.of(context)
                              .textTheme
                              .bodyLarge
                              ?.copyWith(color: scheme.primary),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Speak your order and I will build your cart.',
                          style: Theme.of(context)
                              .textTheme
                              .bodyLarge
                              ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.75)),
                        ),
                      ),
                      const SizedBox(width: 10),
                      if (!voice.connected)
                        FilledButton(
                          onPressed: voice.connecting
                              ? null
                              : () async {
                                  await ref.read(voiceControllerProvider.notifier).start(storeId: storeId);
                                },
                          child: voice.connecting ? const Text('Connecting...') : const Text('Connect'),
                        )
                      else
                        OutlinedButton(
                          onPressed: () async {
                            await ref.read(voiceControllerProvider.notifier).stop();
                          },
                          child: const Text('Disconnect'),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            if (voice.error != null) ...[
              const SizedBox(height: 10),
              Text(
                voice.error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],

            // --- Middle: transcript or placeholder ---
            Expanded(
              child: voice.transcripts.isNotEmpty
                  ? _TranscriptList(transcripts: voice.transcripts)
                  : Padding(
                      padding: const EdgeInsets.only(top: 18),
                      child: Text(
                        'What are you\ncraving?',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                    ),
            ),

            // --- Bottom (pinned) ---
            Center(
              child: Column(
                children: [
                  const SizedBox(height: 8),
                  _Waveform(color: scheme.primary.withValues(alpha: 0.8), width: waveW),
                  const SizedBox(height: 14),
                  _MicOrb(
                    glow: scheme.primary,
                    glow2: scheme.secondary,
                    iconColor: scheme.onPrimary,
                    size: orbSize,
                  ),
                  const SizedBox(height: 14),
                  Text(
                    l10n?.listening ?? 'Listening...',
                    style: Theme.of(context)
                        .textTheme
                        .bodyLarge
                        ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.75)),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '"Order a large pepperoni pizza..."',
                    style: Theme.of(context)
                        .textTheme
                        .bodyLarge
                        ?.copyWith(color: scheme.primary.withValues(alpha: 0.9), fontWeight: FontWeight.w600),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 10),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _TranscriptList extends StatelessWidget {
  final List<TranscriptEntry> transcripts;

  const _TranscriptList({required this.transcripts});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListView.builder(
      reverse: true,
      padding: const EdgeInsets.symmetric(vertical: 12),
      itemCount: transcripts.length,
      itemBuilder: (context, i) {
        final entry = transcripts[transcripts.length - 1 - i];
        final isUser = entry.speaker == 'user';
        return Align(
          alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isUser
                  ? scheme.primary.withValues(alpha: 0.15)
                  : scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(16),
                topRight: const Radius.circular(16),
                bottomLeft: Radius.circular(isUser ? 16 : 4),
                bottomRight: Radius.circular(isUser ? 4 : 16),
              ),
            ),
            child: Text(
              entry.text,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: isUser ? scheme.primary : scheme.onSurface,
                  ),
            ),
          ),
        );
      },
    );
  }
}

/// Post-session view: order summary + rating survey + new order button.
class _PostSessionView extends ConsumerWidget {
  final String storeName;
  final String storeId;

  const _PostSessionView({required this.storeName, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final voice = ref.watch(voiceControllerProvider);

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Session Complete',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),

          // --- Order Summary ---
          AppStage(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Order Summary',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                if (voice.orderItems != null && voice.orderItems!.isNotEmpty) ...[
                  ...voice.orderItems!.map((item) {
                    final lineTotal = item.priceSnapshot * item.quantity;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${item.name ?? 'Item'} x${item.quantity}',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                          ),
                          Text(
                            '\$${lineTotal.toStringAsFixed(2)}',
                            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                        ],
                      ),
                    );
                  }),
                  const Divider(height: 20),
                  _SummaryRow(label: 'Subtotal', value: voice.orderSummary!.subtotal),
                  const SizedBox(height: 4),
                  _SummaryRow(label: 'Tax', value: voice.orderSummary!.tax),
                  const SizedBox(height: 4),
                  _SummaryRow(label: 'Total', value: voice.orderSummary!.total, bold: true),
                ] else
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(
                      'No items were ordered.',
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            color: scheme.onSurface.withValues(alpha: 0.6),
                          ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // --- Rating Survey ---
          AppStage(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'How was your experience?',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                if (voice.ratingSubmitted)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle, color: scheme.primary, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          'Thanks for your feedback!',
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: scheme.primary),
                        ),
                      ],
                    ),
                  )
                else ...[
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: List.generate(10, (i) {
                      final n = i + 1;
                      final selected = voice.rating == n;
                      return SizedBox(
                        width: 40,
                        height: 40,
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            padding: EdgeInsets.zero,
                            backgroundColor: selected ? scheme.primary : null,
                            foregroundColor: selected ? scheme.onPrimary : scheme.onSurface,
                            side: BorderSide(
                              color: selected ? scheme.primary : scheme.outline.withValues(alpha: 0.5),
                            ),
                          ),
                          onPressed: () {
                            ref.read(voiceControllerProvider.notifier).submitRating(n);
                          },
                          child: Text('$n', style: const TextStyle(fontSize: 14)),
                        ),
                      );
                    }),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),

          // --- New Order Button ---
          FilledButton.icon(
            onPressed: () {
              ref.read(voiceControllerProvider.notifier).resetSession();
            },
            icon: const Icon(Icons.replay),
            label: const Text('New Order'),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final double value;
  final bool bold;

  const _SummaryRow({required this.label, required this.value, this.bold = false});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: bold ? FontWeight.bold : FontWeight.normal,
              ),
        ),
        Text(
          '\$${value.toStringAsFixed(2)}',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: bold ? FontWeight.bold : FontWeight.w600,
              ),
        ),
      ],
    );
  }
}

class _MicOrb extends StatelessWidget {
  final Color glow;
  final Color glow2;
  final Color iconColor;
  final double size;

  const _MicOrb({required this.glow, required this.glow2, required this.iconColor, this.size = 110});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final innerSize = size * 62 / 110;
    final iconSize = size * 30 / 110;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            glow.withValues(alpha: 0.35),
            glow2.withValues(alpha: 0.22),
            scheme.surfaceContainerHighest.withValues(alpha: 0.12),
          ],
          stops: const [0.0, 0.55, 1.0],
        ),
        border: Border.all(color: scheme.outline.withValues(alpha: 0.6)),
        boxShadow: [
          BoxShadow(
            color: glow.withValues(alpha: 0.35),
            blurRadius: 24,
            spreadRadius: 6,
          ),
        ],
      ),
      child: Center(
        child: Container(
          width: innerSize,
          height: innerSize,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: scheme.primary,
            boxShadow: [
              BoxShadow(
                color: glow.withValues(alpha: 0.25),
                blurRadius: 18,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Icon(Icons.mic, color: iconColor, size: iconSize),
        ),
      ),
    );
  }
}

class _Waveform extends StatelessWidget {
  final Color color;
  final double width;

  const _Waveform({required this.color, this.width = 260});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: 46,
      child: CustomPaint(
        painter: _WaveformPainter(color: color),
      ),
    );
  }
}

class _WaveformPainter extends CustomPainter {
  final Color color;

  _WaveformPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round
      ..color = color;

    final path = Path();
    final mid = size.height / 2;

    path.moveTo(0, mid);

    // Simple symmetric waves to suggest "listening".
    for (var i = 0; i <= 12; i++) {
      final x = size.width * (i / 12.0);
      final amp = (i == 6 ? 1.0 : (1.0 - (i - 6).abs() / 6.0)) * (size.height * 0.32);
      final y = mid + (i.isEven ? -amp : amp);
      path.quadraticBezierTo(x, y, x, mid);
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WaveformPainter oldDelegate) {
    return oldDelegate.color != color;
  }
}
