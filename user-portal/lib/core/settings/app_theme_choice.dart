import 'package:liquid_glass_flutter/liquid_glass_flutter.dart';

enum AppThemeChoice {
  luxlunch,
  dark,
  light,
  ocean,
  sunset,
  forest,
  contrast,
}

extension AppThemeChoiceX on AppThemeChoice {
  String get code {
    return name;
  }

  static AppThemeChoice fromCode(String? raw, {AppThemeChoice fallback = AppThemeChoice.luxlunch}) {
    final v = (raw ?? '').toLowerCase();
    for (final t in AppThemeChoice.values) {
      if (t.name.toLowerCase() == v) return t;
    }
    return fallback;
  }

  /// Base theme used by [GlassTheme] when no explicit [GlassThemeData] override is provided.
  GlassThemeName get glassThemeName {
    switch (this) {
      case AppThemeChoice.luxlunch:
        return GlassThemeName.dark;
      case AppThemeChoice.dark:
        return GlassThemeName.dark;
      case AppThemeChoice.light:
        return GlassThemeName.light;
      case AppThemeChoice.ocean:
        return GlassThemeName.ocean;
      case AppThemeChoice.sunset:
        return GlassThemeName.sunset;
      case AppThemeChoice.forest:
        return GlassThemeName.forest;
      case AppThemeChoice.contrast:
        return GlassThemeName.contrast;
    }
  }
}
