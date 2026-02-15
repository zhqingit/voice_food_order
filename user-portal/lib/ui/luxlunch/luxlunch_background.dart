import 'package:flutter/widgets.dart';

class LuxLunchBackground {
  static const Color _base = Color(0xFFF4F1EA);

  static BoxDecoration decoration() {
    return const BoxDecoration(
      color: _base,
      gradient: RadialGradient(
        center: Alignment(-0.4, -0.6),
        radius: 1.25,
        colors: [
          Color.fromRGBO(255, 229, 200, 0.55),
          Color.fromRGBO(255, 206, 155, 0.40),
          Color.fromRGBO(214, 232, 214, 0.28),
          _base,
        ],
        stops: [0.0, 0.4, 0.68, 1.0],
      ),
    );
  }
}
