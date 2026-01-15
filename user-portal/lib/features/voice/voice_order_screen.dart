import 'package:flutter/material.dart';

import '../../core/app_theme.dart';

class VoiceOrderScreen extends StatelessWidget {
  final String storeName;

  const VoiceOrderScreen({super.key, required this.storeName});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(storeName),
      ),
      body: Container(
        decoration: AppTheme.backgroundGradient(),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: scheme.outline.withValues(alpha: 0.6)),
                        color: scheme.surfaceContainerHighest.withValues(alpha: 0.35),
                      ),
                      child: Icon(Icons.person_outline, color: scheme.onSurface.withValues(alpha: 0.85)),
                    ),
                    const SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Good Evening,',
                          style: Theme.of(context)
                              .textTheme
                              .bodyLarge
                              ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.65)),
                        ),
                        Text(
                          'Guest',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),
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
                  height: 170,
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
                const Spacer(),
                Center(
                  child: Column(
                    children: [
                      _Waveform(color: scheme.primary.withValues(alpha: 0.8)),
                      const SizedBox(height: 14),
                      _MicOrb(
                        glow: scheme.primary,
                        glow2: scheme.secondary,
                        iconColor: scheme.onPrimary,
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'Listening…',
                        style: Theme.of(context)
                            .textTheme
                            .bodyLarge
                            ?.copyWith(color: scheme.onSurface.withValues(alpha: 0.75)),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        '“Order a large pepperoni pizza…”',
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

  const _MicOrb({required this.glow, required this.glow2, required this.iconColor});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Container(
      width: 110,
      height: 110,
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
          width: 62,
          height: 62,
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
          child: Icon(Icons.mic, color: iconColor, size: 30),
        ),
      ),
    );
  }
}

class _Waveform extends StatelessWidget {
  final Color color;

  const _Waveform({required this.color});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 260,
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
