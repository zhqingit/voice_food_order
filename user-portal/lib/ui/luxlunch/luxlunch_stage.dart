import 'dart:ui';

import 'package:flutter/widgets.dart';

class LuxLunchStage extends StatelessWidget {
  final Widget child;

  const LuxLunchStage({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(26),
      child: Stack(
        children: [
          const Positioned.fill(child: _StageBackground()),
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(
                    color: const Color.fromRGBO(255, 255, 255, 0.45),
                    width: 1,
                  ),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color.fromRGBO(255, 255, 255, 0.45),
                      Color.fromRGBO(255, 255, 255, 0.22),
                    ],
                  ),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: child,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StageBackground extends StatelessWidget {
  const _StageBackground();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(26)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color.fromRGBO(255, 255, 255, 0.55),
            Color.fromRGBO(235, 225, 205, 0.50),
          ],
        ),
      ),
      child: const DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.all(Radius.circular(26)),
          gradient: RadialGradient(
            center: Alignment(-0.3, -0.4),
            radius: 1.1,
            colors: [
              Color.fromRGBO(255, 255, 255, 0.55),
              Color.fromRGBO(255, 255, 255, 0.15),
            ],
            stops: [0.0, 0.7],
          ),
        ),
      ),
    );
  }
}
