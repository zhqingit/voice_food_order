import 'package:flutter/painting.dart';

class AppAccent {
  static const Color orangeA = Color(0xFFFFB15A);
  static const Color orangeB = Color(0xFFFF8A2A);
  static const Color softGreen = Color(0xFF6FAF7A);

  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color.fromRGBO(255, 177, 90, 0.95),
      Color.fromRGBO(255, 138, 42, 0.92),
    ],
  );
}
