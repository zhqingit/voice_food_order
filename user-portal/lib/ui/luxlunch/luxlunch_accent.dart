import 'package:flutter/painting.dart';

class LuxLunchAccent {
  static const Color orangeA = Color(0xFFFFB24A);
  static const Color orangeB = Color(0xFFFF7A1A);

  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color.fromRGBO(255, 178, 74, 0.95),
      Color.fromRGBO(255, 122, 26, 0.92),
    ],
  );
}
