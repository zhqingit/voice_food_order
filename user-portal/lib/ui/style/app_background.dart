import 'package:flutter/widgets.dart';

class AppBackground {
  static const Color _base = Color(0xFFE9E4D8);

  static BoxDecoration decoration() {
    return const BoxDecoration(
      color: _base,
      gradient: RadialGradient(
        center: Alignment(-0.35, -0.45),
        radius: 1.25,
        colors: [
          Color.fromRGBO(250, 235, 215, 0.65),
          Color.fromRGBO(230, 223, 205, 0.60),
          Color.fromRGBO(210, 220, 210, 0.45),
          _base,
        ],
        stops: [0.0, 0.38, 0.68, 1.0],
      ),
    );
  }
}
