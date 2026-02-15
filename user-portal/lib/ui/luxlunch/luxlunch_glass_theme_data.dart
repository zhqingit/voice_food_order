import 'package:flutter/painting.dart';
import 'package:liquid_glass_flutter/liquid_glass_flutter.dart';

/// LuxLunch-inspired glass tokens (ported from liquid_glass_react/apps/playground).
///
/// This overrides the base [GlassThemeData] to feel a bit warmer with stronger
/// highlights and a slightly "crystal" border.
GlassThemeData luxLunchGlassThemeData() {
  return const GlassThemeData(
    borderRadius: 22,
    blurSigma: 22,
    tintColor: Color.fromRGBO(20, 22, 28, 0.34),
    borderColor: Color.fromRGBO(255, 255, 255, 0.18),
    highlightColor: Color.fromRGBO(255, 235, 210, 0.38),
    highlightStrength: 0.95,
    shadowColor: Color.fromRGBO(0, 0, 0, 0.55),
    shadowOffset: Offset(0, 14),
    shadowBlurRadius: 44,
    innerHighlightColor: Color.fromRGBO(255, 255, 255, 0.14),
    noiseOpacity: 0.06,
  );
}
