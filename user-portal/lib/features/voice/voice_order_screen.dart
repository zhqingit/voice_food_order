import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_theme.dart';
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
    final scheme = Theme.of(context).colorScheme;
    final voice = ref.watch(voiceControllerProvider);

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
            child: LayoutBuilder(
              builder: (context, constraints) {
                final h = constraints.maxHeight;
                final suggestionH = (h * 0.2).clamp(120.0, 170.0);
                final logsH = (h * 0.15).clamp(100.0, 160.0);
                final orbSize = h < 600 ? 80.0 : 110.0;
                final waveW = (h * 0.35).clamp(180.0, 260.0);

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // --- Header (intrinsic height) ---
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
                          const SizedBox(height: 6),
                          Text(
                            'store_id: $storeId',
                            style: Theme.of(context)
                                .textTheme
                                .bodyLarge
                                ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.65)),
                            overflow: TextOverflow.ellipsis,
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
                                  child: voice.connecting ? const Text('Connecting…') : const Text('Connect'),
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

                    // --- Middle (scrollable) ---
                    Expanded(
                      child: SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 18),
                            Text(
                              'What are you\ncraving?',
                              style: Theme.of(context).textTheme.headlineLarge,
                            ),
                            const SizedBox(height: 14),
                            Text(
                              'Suggested',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyLarge
                                  ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.7), fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 12),
                            SizedBox(
                              height: suggestionH,
                              child: ListView(
                                scrollDirection: Axis.horizontal,
                                children: const [
                                  _SuggestionCard(title: 'Cyber Sushi Roll', price: '\$18.50'),
                                  SizedBox(width: 12),
                                  _SuggestionCard(title: 'Futuristic Pizza', price: '\$18.50'),
                                  SizedBox(width: 12),
                                  _SuggestionCard(title: 'Neon Burger', price: '\$12.90'),
                                ],
                              ),
                            ),
                            if (voice.logs.isNotEmpty) ...[
                              const SizedBox(height: 12),
                              Container(
                                height: logsH,
                                decoration: AppTheme.glassCardDecoration(context),
                                padding: const EdgeInsets.all(10),
                                child: ListView.builder(
                                  reverse: true,
                                  itemCount: voice.logs.length,
                                  itemBuilder: (context, i) {
                                    final line = voice.logs[voice.logs.length - 1 - i];
                                    return Text(
                                      line,
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodyLarge
                                          ?.copyWith(fontSize: 12, color: scheme.onSurface.withValues(alpha: 0.75)),
                                    );
                                  },
                                ),
                              ),
                            ],
                          ],
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
                            l10n?.listening ?? 'Listening…',
                            style: Theme.of(context)
                                .textTheme
                                .bodyLarge
                                ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.75)),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            '”Order a large pepperoni pizza…”',
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
            ),
          ),
        ),
      ),
    );
  }
}

class _SuggestionCard extends StatelessWidget {
  final String title;
  final String price;

  const _SuggestionCard({required this.title, required this.price});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Container(
      width: 150,
      decoration: AppTheme.glassCardDecoration(context),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: scheme.surface.withValues(alpha: 0.35),
                border: Border.all(color: scheme.outline.withValues(alpha: 0.35)),
              ),
              child: Center(
                child: Icon(Icons.restaurant_menu, color: scheme.onSurface.withValues(alpha: 0.75)),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            price,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: scheme.primary.withValues(alpha: 0.9)),
          ),
        ],
      ),
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
