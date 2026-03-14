import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/menu_models.dart';
import '../../data/menu_repository.dart';
import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import 'voice_controller.dart';

final menuRepositoryProvider = Provider<MenuRepository>((ref) {
  return MenuRepository(ref.watch(apiClientProvider).dio);
});

const _kOrangeStart = Color(0xFFFF8A2A);
const _kOrangeEnd = Color(0xFFFFB15A);
const _kTextDark = Color(0xFF2E241A);
const _kTextMuted = Color(0xFF6D5D4B);
const _kCardBg = Color(0xFFFFFBF5);
const _kUserBubble = Color(0xFFFF8A2A);
const _kBotBubble = Colors.white;
const _kStarActive = Color(0xFFFFB15A);
const _kStarInactive = Color(0xFFE0D6C8);

class VoiceOrderScreen extends ConsumerWidget {
  final String storeName;
  final String storeId;

  const VoiceOrderScreen({super.key, required this.storeName, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voice = ref.watch(voiceControllerProvider);
    final showPostSession = voice.sessionEnded && !voice.connected;

    return Scaffold(
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.9),
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 8, offset: const Offset(0, 2))],
            ),
            child: const Icon(Icons.arrow_back_ios_new, size: 18, color: Color(0xFF3D3D3D)),
          ),
          onPressed: () => Navigator.of(context).pop(),
        ),
        centerTitle: true,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(storeName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: _kTextDark)),
            const SizedBox(width: 8),
            _ConnectionDot(connected: voice.connected, connecting: voice.connecting),
          ],
        ),
        actions: [
          IconButton(
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.9),
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 8, offset: const Offset(0, 2))],
              ),
              child: const Icon(Icons.restaurant_menu_rounded, size: 18, color: _kOrangeStart),
            ),
            onPressed: () => _showMenuSheet(context, storeId),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 400),
            switchInCurve: Curves.easeOut,
            child: showPostSession
                ? _PostSessionView(key: const ValueKey('post'), storeName: storeName, storeId: storeId)
                : _ActiveSessionView(key: const ValueKey('active'), storeName: storeName, storeId: storeId),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Connection indicator dot
// ---------------------------------------------------------------------------

class _ConnectionDot extends StatefulWidget {
  final bool connected;
  final bool connecting;

  const _ConnectionDot({required this.connected, required this.connecting});

  @override
  State<_ConnectionDot> createState() => _ConnectionDotState();
}

class _ConnectionDotState extends State<_ConnectionDot> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final showPulse = widget.connected || widget.connecting;
    final color = widget.connected ? const Color(0xFF66BB6A) : _kOrangeStart;

    if (!showPulse) {
      return Container(
        width: 10, height: 10,
        decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.grey.withValues(alpha: 0.4)),
      );
    }

    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) {
        final scale = 1.0 + _ctrl.value * 0.5;
        return SizedBox(
          width: 16, height: 16,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Transform.scale(
                scale: scale,
                child: Container(
                  width: 10, height: 10,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: color.withValues(alpha: 0.3 * (1 - _ctrl.value))),
                ),
              ),
              Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: color)),
            ],
          ),
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Active session view
// ---------------------------------------------------------------------------

class _ActiveSessionView extends ConsumerWidget {
  final String storeName;
  final String storeId;

  const _ActiveSessionView({super.key, required this.storeName, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final voice = ref.watch(voiceControllerProvider);

    String statusText;
    if (voice.connected) {
      statusText = l10n?.listening ?? 'Listening...';
    } else if (voice.connecting) {
      statusText = l10n?.connecting ?? 'Connecting...';
    } else {
      statusText = l10n?.tapMicToStart ?? 'Tap the mic to start';
    }

    return Column(
      children: [
        // Live order summary (slides in when items are added)
        if (voice.liveOrder != null && voice.liveOrder!.items.isNotEmpty)
          _LiveOrderPanel(order: voice.liveOrder!),

        // Transcript area
        Expanded(
          child: voice.transcripts.isNotEmpty
              ? _TranscriptList(transcripts: voice.transcripts)
              : Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 40),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.restaurant_menu_rounded, size: 48, color: _kOrangeEnd.withValues(alpha: 0.4)),
                        const SizedBox(height: 16),
                        Text(
                          l10n?.whatAreYouCraving ?? 'What are you\ncraving?',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: _kTextDark.withValues(alpha: 0.3), height: 1.2),
                        ),
                      ],
                    ),
                  ),
                ),
        ),

        if (voice.error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(color: const Color(0xFFFFF0E6), borderRadius: BorderRadius.circular(12)),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded, color: Color(0xFFCC4B00), size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(voice.error!, style: const TextStyle(color: Color(0xFFCC4B00), fontSize: 13))),
                ],
              ),
            ),
          ),

        // Mic orb + status
        Padding(
          padding: const EdgeInsets.only(bottom: 32, top: 16),
          child: Column(
            children: [
              _AnimatedWaveform(active: voice.connected),
              const SizedBox(height: 16),
              _AnimatedMicOrb(
                connected: voice.connected,
                connecting: voice.connecting,
                onTap: () async {
                  if (voice.connected) {
                    await ref.read(voiceControllerProvider.notifier).stop();
                  } else if (!voice.connecting) {
                    await ref.read(voiceControllerProvider.notifier).start(storeId: storeId);
                  }
                },
              ),
              const SizedBox(height: 14),
              Text(statusText, style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: _kTextMuted.withValues(alpha: 0.8))),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Animated mic orb
// ---------------------------------------------------------------------------

class _AnimatedMicOrb extends StatefulWidget {
  final bool connected;
  final bool connecting;
  final VoidCallback onTap;

  const _AnimatedMicOrb({required this.connected, required this.connecting, required this.onTap});

  @override
  State<_AnimatedMicOrb> createState() => _AnimatedMicOrbState();
}

class _AnimatedMicOrbState extends State<_AnimatedMicOrb> with TickerProviderStateMixin {
  late final AnimationController _pulseCtrl;
  late final AnimationController _ringCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));
    _ringCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 2000));
    _updateAnimation();
  }

  @override
  void didUpdateWidget(covariant _AnimatedMicOrb old) {
    super.didUpdateWidget(old);
    if (old.connected != widget.connected || old.connecting != widget.connecting) {
      _updateAnimation();
    }
  }

  void _updateAnimation() {
    if (widget.connected) {
      _pulseCtrl.repeat(reverse: true);
      _ringCtrl.repeat();
    } else if (widget.connecting) {
      _pulseCtrl.repeat(reverse: true);
      _ringCtrl.stop();
    } else {
      _pulseCtrl.stop();
      _pulseCtrl.value = 0;
      _ringCtrl.stop();
      _ringCtrl.value = 0;
    }
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _ringCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const size = 110.0;
    const innerSize = 68.0;

    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: size + 40,
        height: size + 40,
        child: AnimatedBuilder(
          animation: Listenable.merge([_pulseCtrl, _ringCtrl]),
          builder: (_, __) {
            final pulse = _pulseCtrl.value;
            final ring = _ringCtrl.value;

            return Stack(
              alignment: Alignment.center,
              children: [
                // Expanding rings
                if (widget.connected) ...[
                  for (var i = 0; i < 3; i++)
                    _buildRing(size, ring, i),
                ],

                // Outer glow
                Container(
                  width: size + pulse * 8,
                  height: size + pulse * 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        _kOrangeStart.withValues(alpha: 0.25 + pulse * 0.1),
                        _kOrangeEnd.withValues(alpha: 0.12),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.6, 1.0],
                    ),
                  ),
                ),

                // Inner orb
                Container(
                  width: innerSize,
                  height: innerSize,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [_kOrangeStart, _kOrangeEnd],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    boxShadow: [
                      BoxShadow(color: _kOrangeStart.withValues(alpha: 0.4 + pulse * 0.15), blurRadius: 20 + pulse * 8, spreadRadius: pulse * 2),
                    ],
                  ),
                  child: Icon(
                    widget.connected ? Icons.stop_rounded : Icons.mic_rounded,
                    color: Colors.white,
                    size: 30,
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildRing(double baseSize, double progress, int index) {
    final offset = (progress + index / 3.0) % 1.0;
    final ringSize = baseSize + offset * 50;
    final opacity = (1.0 - offset) * 0.3;

    return Container(
      width: ringSize,
      height: ringSize,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: _kOrangeStart.withValues(alpha: opacity), width: 1.5),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Animated waveform
// ---------------------------------------------------------------------------

class _AnimatedWaveform extends StatefulWidget {
  final bool active;

  const _AnimatedWaveform({required this.active});

  @override
  State<_AnimatedWaveform> createState() => _AnimatedWaveformState();
}

class _AnimatedWaveformState extends State<_AnimatedWaveform> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));
    if (widget.active) _ctrl.repeat();
  }

  @override
  void didUpdateWidget(covariant _AnimatedWaveform old) {
    super.didUpdateWidget(old);
    if (widget.active && !_ctrl.isAnimating) {
      _ctrl.repeat();
    } else if (!widget.active && _ctrl.isAnimating) {
      _ctrl.stop();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 200,
      height: 40,
      child: AnimatedBuilder(
        animation: _ctrl,
        builder: (_, __) => CustomPaint(painter: _WaveformPainter(phase: _ctrl.value, active: widget.active)),
      ),
    );
  }
}

class _WaveformPainter extends CustomPainter {
  final double phase;
  final bool active;

  _WaveformPainter({required this.phase, required this.active});

  @override
  void paint(Canvas canvas, Size size) {
    const barCount = 24;
    final barWidth = size.width / (barCount * 2);
    final maxHeight = size.height * 0.8;
    final mid = size.height / 2;

    final paint = Paint()
      ..style = PaintingStyle.fill
      ..strokeCap = StrokeCap.round;

    for (var i = 0; i < barCount; i++) {
      final x = barWidth + i * (size.width - barWidth * 2) / (barCount - 1);
      final normalizedI = (i - barCount / 2).abs() / (barCount / 2);
      final baseHeight = (1.0 - normalizedI * 0.7) * maxHeight;

      double h;
      if (active) {
        final wave = math.sin((phase * math.pi * 2) + i * 0.5) * 0.4 + 0.6;
        h = baseHeight * wave;
      } else {
        h = 3.0;
      }

      final gradient = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [_kOrangeStart.withValues(alpha: active ? 0.8 : 0.2), _kOrangeEnd.withValues(alpha: active ? 0.5 : 0.1)],
      );

      paint.shader = gradient.createShader(Rect.fromCenter(center: Offset(x, mid), width: barWidth, height: h));

      final rr = RRect.fromRectAndRadius(
        Rect.fromCenter(center: Offset(x, mid), width: barWidth * 0.7, height: h),
        Radius.circular(barWidth),
      );
      canvas.drawRRect(rr, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _WaveformPainter old) => old.phase != phase || old.active != active;
}

// ---------------------------------------------------------------------------
// Live order panel (shown during active session)
// ---------------------------------------------------------------------------

class _LiveOrderPanel extends StatefulWidget {
  final LiveOrderSummary order;

  const _LiveOrderPanel({required this.order});

  @override
  State<_LiveOrderPanel> createState() => _LiveOrderPanelState();
}

class _LiveOrderPanelState extends State<_LiveOrderPanel> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final order = widget.order;
    final itemCount = order.items.fold<int>(0, (sum, i) => sum + i.quantity);

    return AnimatedSize(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
      alignment: Alignment.topCenter,
      child: Container(
        margin: const EdgeInsets.fromLTRB(16, 4, 16, 4),
        decoration: BoxDecoration(
          color: _kCardBg,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 12, offset: const Offset(0, 3)),
          ],
        ),
        child: Column(
          children: [
            // Header (always visible, tap to expand/collapse)
            GestureDetector(
              onTap: () => setState(() => _expanded = !_expanded),
              behavior: HitTestBehavior.opaque,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(color: _kOrangeEnd.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(8)),
                      child: const Icon(Icons.receipt_long_rounded, size: 16, color: _kOrangeStart),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      '$itemCount ${itemCount == 1 ? (l10n?.item ?? "Item") : (l10n?.item ?? "Items")}',
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: _kTextDark),
                    ),
                    const Spacer(),
                    Text(
                      '\$${order.total.toStringAsFixed(2)}',
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: _kOrangeStart),
                    ),
                    const SizedBox(width: 6),
                    AnimatedRotation(
                      turns: _expanded ? 0.5 : 0,
                      duration: const Duration(milliseconds: 200),
                      child: const Icon(Icons.keyboard_arrow_down_rounded, size: 20, color: _kTextMuted),
                    ),
                  ],
                ),
              ),
            ),

            // Expanded details
            if (_expanded) ...[
              Divider(height: 1, color: Colors.grey.withValues(alpha: 0.12), indent: 16, endIndent: 16),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: Column(
                  children: [
                    ...order.items.map((item) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Container(
                            width: 22, height: 22,
                            decoration: BoxDecoration(color: _kOrangeEnd.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6)),
                            child: Center(child: Text('${item.quantity}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _kOrangeStart))),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(item.name, style: const TextStyle(fontSize: 13, color: _kTextDark)),
                                if (item.note != null && item.note!.isNotEmpty)
                                  Text(item.note!, style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: _kTextMuted.withValues(alpha: 0.8))),
                              ],
                            ),
                          ),
                          Text('\$${item.lineTotal.toStringAsFixed(2)}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: _kTextDark)),
                        ],
                      ),
                    )),
                    const SizedBox(height: 6),
                    Divider(height: 1, color: Colors.grey.withValues(alpha: 0.1)),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(l10n?.subtotal ?? 'Subtotal', style: TextStyle(fontSize: 12, color: _kTextMuted.withValues(alpha: 0.8))),
                        Text('\$${order.subtotal.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _kTextDark)),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(l10n?.tax ?? 'Tax', style: TextStyle(fontSize: 12, color: _kTextMuted.withValues(alpha: 0.8))),
                        Text('\$${order.tax.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _kTextDark)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(l10n?.total ?? 'Total', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: _kTextDark)),
                        Text('\$${order.total.toStringAsFixed(2)}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: _kOrangeStart)),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Transcript list
// ---------------------------------------------------------------------------

class _TranscriptList extends StatelessWidget {
  final List<TranscriptEntry> transcripts;

  const _TranscriptList({required this.transcripts});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      reverse: true,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      itemCount: transcripts.length,
      itemBuilder: (context, i) {
        final entry = transcripts[transcripts.length - 1 - i];
        final isUser = entry.speaker == 'user';

        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isUser) ...[
                Container(
                  width: 28, height: 28,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(colors: [_kOrangeStart.withValues(alpha: 0.2), _kOrangeEnd.withValues(alpha: 0.15)]),
                  ),
                  child: const Icon(Icons.auto_awesome, size: 14, color: _kOrangeStart),
                ),
                const SizedBox(width: 8),
              ],
              Flexible(
                child: Container(
                  constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.72),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: isUser ? _kUserBubble : _kBotBubble,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(18),
                      topRight: const Radius.circular(18),
                      bottomLeft: Radius.circular(isUser ? 18 : 4),
                      bottomRight: Radius.circular(isUser ? 4 : 18),
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: isUser ? 0.08 : 0.05), blurRadius: 8, offset: const Offset(0, 2)),
                    ],
                  ),
                  child: Text(
                    entry.text,
                    style: TextStyle(fontSize: 15, height: 1.4, color: isUser ? Colors.white : _kTextDark),
                  ),
                ),
              ),
              if (isUser) ...[
                const SizedBox(width: 8),
                Container(
                  width: 28, height: 28,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: _kOrangeStart.withValues(alpha: 0.15)),
                  child: const Icon(Icons.person, size: 14, color: _kOrangeStart),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Post-session view
// ---------------------------------------------------------------------------

class _PostSessionView extends ConsumerWidget {
  final String storeName;
  final String storeId;

  const _PostSessionView({super.key, required this.storeName, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Success header
          Center(
            child: Column(
              children: [
                Container(
                  width: 72, height: 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(colors: [_kOrangeStart, _kOrangeEnd]),
                    boxShadow: [BoxShadow(color: _kOrangeStart.withValues(alpha: 0.3), blurRadius: 16, offset: const Offset(0, 6))],
                  ),
                  child: const Icon(Icons.check_rounded, color: Colors.white, size: 36),
                ),
                const SizedBox(height: 16),
                Text(l10n?.sessionComplete ?? 'Session Complete', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: _kTextDark)),
                const SizedBox(height: 4),
                Text(l10n?.thanksForOrdering(storeName) ?? 'Thanks for ordering at $storeName', style: TextStyle(fontSize: 14, color: _kTextMuted.withValues(alpha: 0.8))),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Review & Rating
          _ReviewCard(storeName: storeName),
          const SizedBox(height: 24),

          // New order button
          GestureDetector(
            onTap: () => ref.read(voiceControllerProvider.notifier).resetSession(),
            child: Container(
              height: 52,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                gradient: const LinearGradient(colors: [_kOrangeStart, _kOrangeEnd]),
                boxShadow: [BoxShadow(color: _kOrangeStart.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.replay_rounded, color: Colors.white, size: 20),
                  const SizedBox(width: 8),
                  Text(l10n?.newOrder ?? 'New Order', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Review card (rating + text review)
// ---------------------------------------------------------------------------

class _ReviewCard extends ConsumerStatefulWidget {
  final String storeName;

  const _ReviewCard({required this.storeName});

  @override
  ConsumerState<_ReviewCard> createState() => _ReviewCardState();
}

class _ReviewCardState extends ConsumerState<_ReviewCard> {
  final _reviewController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _reviewController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final voice = ref.watch(voiceControllerProvider);
    final allSubmitted = voice.ratingSubmitted && voice.reviewSubmitted;

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: _kStarActive.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(10)),
                child: const Icon(Icons.rate_review_rounded, size: 20, color: _kStarActive),
              ),
              const SizedBox(width: 12),
              Text(l10n?.howWasExperience ?? 'How was your experience?', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: _kTextDark)),
            ],
          ),
          const SizedBox(height: 20),

          // Star rating
          Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(5, (i) {
                final starValue = i + 1;
                final apiValue = starValue * 2;
                final selected = voice.rating != null && voice.rating! >= apiValue;
                return GestureDetector(
                  onTap: allSubmitted ? null : () => ref.read(voiceControllerProvider.notifier).submitRating(apiValue),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    child: AnimatedScale(
                      scale: selected ? 1.2 : 1.0,
                      duration: const Duration(milliseconds: 200),
                      child: Icon(
                        selected ? Icons.star_rounded : Icons.star_outline_rounded,
                        size: 40,
                        color: selected ? _kStarActive : _kStarInactive,
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(height: 20),

          // Review text field
          if (allSubmitted)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(color: const Color(0xFFE8F5E9), borderRadius: BorderRadius.circular(12)),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_rounded, color: Color(0xFF66BB6A), size: 20),
                  const SizedBox(width: 10),
                  Text(l10n?.thanksForFeedback ?? 'Thanks for your feedback!', style: const TextStyle(color: Color(0xFF2E7D32), fontWeight: FontWeight.w600, fontSize: 14)),
                ],
              ),
            )
          else ...[
            TextField(
              controller: _reviewController,
              maxLines: 3,
              maxLength: 500,
              textInputAction: TextInputAction.done,
              style: const TextStyle(fontSize: 15, color: _kTextDark),
              decoration: InputDecoration(
                hintText: 'Tell us about your experience...',
                hintStyle: TextStyle(color: _kTextMuted.withValues(alpha: 0.5)),
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.all(16),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.2))),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.2))),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: _kOrangeStart, width: 1.5)),
                counterStyle: TextStyle(fontSize: 11, color: _kTextMuted.withValues(alpha: 0.5)),
              ),
            ),
            const SizedBox(height: 14),

            // Submit button
            GestureDetector(
              onTap: _submitting ? null : () async {
                setState(() => _submitting = true);
                final notifier = ref.read(voiceControllerProvider.notifier);
                // Submit review if text is provided
                if (_reviewController.text.trim().isNotEmpty) {
                  await notifier.submitReview(_reviewController.text);
                } else {
                  // If no text but rating exists, just mark review as submitted
                  if (voice.ratingSubmitted) {
                    // Already has rating, mark complete
                  }
                }
                setState(() => _submitting = false);
              },
              child: Container(
                width: double.infinity,
                height: 48,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  gradient: const LinearGradient(colors: [_kOrangeStart, _kOrangeEnd]),
                  boxShadow: [BoxShadow(color: _kOrangeStart.withValues(alpha: 0.25), blurRadius: 12, offset: const Offset(0, 4))],
                ),
                child: Center(
                  child: _submitting
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(
                          'Submit Review',
                          style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700),
                        ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Menu bottom sheet
// ---------------------------------------------------------------------------

void _showMenuSheet(BuildContext context, String storeId) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => DraggableScrollableSheet(
      initialChildSize: 0.6,
      minChildSize: 0.3,
      maxChildSize: 0.9,
      builder: (context, scrollController) => _MenuSheet(
        storeId: storeId,
        scrollController: scrollController,
      ),
    ),
  );
}

class _MenuSheet extends ConsumerStatefulWidget {
  final String storeId;
  final ScrollController scrollController;

  const _MenuSheet({required this.storeId, required this.scrollController});

  @override
  ConsumerState<_MenuSheet> createState() => _MenuSheetState();
}

class _MenuSheetState extends ConsumerState<_MenuSheet> {
  List<MenuItemOut>? _items;
  String? _error;
  String? _selectedCategory;

  @override
  void initState() {
    super.initState();
    _loadMenu();
  }

  Future<void> _loadMenu() async {
    try {
      final repo = ref.read(menuRepositoryProvider);
      final items = await repo.getStoreMenu(widget.storeId);
      if (mounted) setState(() => _items = items);
    } catch (e) {
      if (mounted) setState(() => _error = 'Failed to load menu');
    }
  }

  List<String> get _categories {
    if (_items == null) return [];
    final cats = _items!
        .where((i) => i.category != null && i.category!.isNotEmpty)
        .map((i) => i.category!)
        .toSet()
        .toList()
      ..sort();
    return cats;
  }

  List<MenuItemOut> get _filteredItems {
    if (_items == null) return [];
    if (_selectedCategory == null) return _items!.where((i) => i.availability).toList();
    return _items!.where((i) => i.availability && i.category == _selectedCategory).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: _kCardBg,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Drag handle
          Padding(
            padding: const EdgeInsets.only(top: 12, bottom: 4),
            child: Container(
              width: 40, height: 4,
              decoration: BoxDecoration(color: Colors.grey.withValues(alpha: 0.3), borderRadius: BorderRadius.circular(2)),
            ),
          ),

          // Title
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: _kOrangeEnd.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.restaurant_menu_rounded, size: 20, color: _kOrangeStart),
                ),
                const SizedBox(width: 12),
                const Text('Menu', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: _kTextDark)),
              ],
            ),
          ),

          // Category chips
          if (_categories.isNotEmpty)
            SizedBox(
              height: 44,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                children: [
                  _CategoryChip(
                    label: 'All',
                    selected: _selectedCategory == null,
                    onTap: () => setState(() => _selectedCategory = null),
                  ),
                  ..._categories.map((cat) => _CategoryChip(
                    label: cat,
                    selected: _selectedCategory == cat,
                    onTap: () => setState(() => _selectedCategory = cat),
                  )),
                ],
              ),
            ),

          const SizedBox(height: 4),
          Divider(height: 1, color: Colors.grey.withValues(alpha: 0.12)),

          // Content
          Expanded(
            child: _items == null
                ? (_error != null
                    ? Center(child: Text(_error!, style: const TextStyle(color: _kTextMuted)))
                    : const Center(child: CircularProgressIndicator(color: _kOrangeStart)))
                : _filteredItems.isEmpty
                    ? Center(child: Text('No items available', style: TextStyle(color: _kTextMuted.withValues(alpha: 0.6))))
                    : ListView.separated(
                        controller: widget.scrollController,
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                        itemCount: _filteredItems.length,
                        separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.withValues(alpha: 0.08), indent: 12, endIndent: 12),
                        itemBuilder: (_, i) => _MenuItemTile(item: _filteredItems[i]),
                      ),
          ),
        ],
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _CategoryChip({required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          decoration: BoxDecoration(
            color: selected ? _kOrangeStart : Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: selected ? _kOrangeStart : Colors.grey.withValues(alpha: 0.2)),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: selected ? Colors.white : _kTextMuted,
            ),
          ),
        ),
      ),
    );
  }
}

class _MenuItemTile extends StatelessWidget {
  final MenuItemOut item;

  const _MenuItemTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final hasSizes = item.priceSmall != null || item.priceMedium != null || item.priceLarge != null;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: _kTextDark)),
                if (item.description != null && item.description!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Text(
                      item.description!,
                      style: TextStyle(fontSize: 12, color: _kTextMuted.withValues(alpha: 0.7), height: 1.3),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                if (hasSizes)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Wrap(
                      spacing: 8,
                      children: [
                        if (item.priceSmall != null) _SizePrice(size: 'S', price: item.priceSmall!),
                        if (item.priceMedium != null) _SizePrice(size: 'M', price: item.priceMedium!),
                        if (item.priceLarge != null) _SizePrice(size: 'L', price: item.priceLarge!),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '\$${item.price.toStringAsFixed(2)}',
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: _kOrangeStart),
          ),
        ],
      ),
    );
  }
}

class _SizePrice extends StatelessWidget {
  final String size;
  final double price;

  const _SizePrice({required this.size, required this.price});

  @override
  Widget build(BuildContext context) {
    return Text(
      '$size: \$${price.toStringAsFixed(2)}',
      style: TextStyle(fontSize: 11, color: _kTextMuted.withValues(alpha: 0.7), fontWeight: FontWeight.w500),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared widgets
// ---------------------------------------------------------------------------

class _Card extends StatelessWidget {
  final Widget child;
  const _Card({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _kCardBg,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 20, offset: const Offset(0, 4)),
          BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 6, offset: const Offset(0, 1)),
        ],
      ),
      child: child,
    );
  }
}

