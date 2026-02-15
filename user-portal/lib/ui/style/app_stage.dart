import 'dart:ui';

import 'package:flutter/widgets.dart';

class AppStage extends StatelessWidget {
  final Widget child;

  const AppStage({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(26),
      child: Stack(
        fit: StackFit.passthrough,
        children: [
          const Positioned.fill(child: _StageBackground()),
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(
                    color: const Color.fromRGBO(255, 255, 255, 0.55),
                    width: 1,
                  ),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color.fromRGBO(255, 255, 255, 0.55),
                      Color.fromRGBO(245, 235, 220, 0.30),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 26),
            child: child,
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
            Color.fromRGBO(255, 255, 255, 0.60),
            Color.fromRGBO(220, 214, 200, 0.55),
          ],
        ),
      ),
      child: const DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.all(Radius.circular(26)),
          gradient: RadialGradient(
            center: Alignment(-0.2, -0.3),
            radius: 1.1,
            colors: [
              Color.fromRGBO(255, 255, 255, 0.65),
              Color.fromRGBO(255, 255, 255, 0.15),
            ],
            stops: [0.0, 0.7],
          ),
        ),
      ),
    );
  }
}
