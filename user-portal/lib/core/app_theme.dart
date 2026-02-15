import 'package:flutter/material.dart';

import 'settings/app_theme_choice.dart';

import '../ui/style/app_accent.dart';

class AppTheme {
  static const _bg = Color(0xFFE9E4D8);
  static const _surface = Color(0xFFF8F5EE);
  static const _surface2 = Color(0xFFEFE7DA);
  static const _text = Color.fromRGBO(46, 36, 26, 0.92);

  static ThemeData materialFor(AppThemeChoice choice) {
    final primary = _primaryFor(choice);
    final secondary = _secondaryFor(choice);
    final isSignature = choice == AppThemeChoice.luxlunch;
    final brightness = isSignature ? Brightness.light : Brightness.dark;

    final surface = isSignature ? _surface : const Color(0xFF0E1116);
    final surface2 = isSignature ? _surface2 : const Color(0xFF141922);
    final text = isSignature ? _text : const Color.fromRGBO(255, 255, 255, 0.92);
    final outline = isSignature
      ? const Color.fromRGBO(140, 120, 95, 0.28)
      : Colors.white.withValues(alpha: 0.16);

    final scheme = ColorScheme(
      brightness: brightness,
      primary: primary,
      onPrimary: isSignature ? const Color.fromRGBO(64, 40, 20, 0.95) : const Color.fromRGBO(10, 10, 12, 0.92),
      secondary: secondary,
      onSecondary: isSignature ? const Color.fromRGBO(64, 40, 20, 0.95) : const Color.fromRGBO(10, 10, 12, 0.92),
      error: const Color(0xFFFF5C6C),
      onError: Colors.black,
      surface: surface,
      onSurface: text,
      surfaceContainerHighest: surface2,
      outline: outline,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: isSignature ? _bg : const Color(0xFF07080B),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isSignature ? const Color.fromRGBO(255, 255, 255, 0.75) : Colors.white.withValues(alpha: 0.08),
        hintStyle: TextStyle(color: scheme.onSurface.withValues(alpha: 0.6)),
        labelStyle: TextStyle(color: scheme.onSurface.withValues(alpha: 0.8)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outline.withValues(alpha: 0.9)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outline.withValues(alpha: 0.6)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.primary.withValues(alpha: 0.95), width: 1.6),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontSize: 34, fontWeight: FontWeight.w800, height: 1.05, letterSpacing: -0.3),
        headlineMedium: TextStyle(fontSize: 26, fontWeight: FontWeight.w800),
        titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        bodyLarge: TextStyle(fontSize: 16, height: 1.3),
      ).apply(
        bodyColor: scheme.onSurface,
        displayColor: scheme.onSurface,
      ),
    );
  }

  static Color _primaryFor(AppThemeChoice choice) {
    switch (choice) {
      case AppThemeChoice.luxlunch:
        return AppAccent.orangeA;
      case AppThemeChoice.ocean:
        return const Color(0xFF78B4FF);
      case AppThemeChoice.sunset:
        return const Color(0xFFFF78DC);
      case AppThemeChoice.forest:
        return const Color(0xFF78FFBE);
      case AppThemeChoice.contrast:
        return const Color(0xFFFFFFFF);
      case AppThemeChoice.light:
        return const Color(0xFFEAEFF7);
      case AppThemeChoice.dark:
        return AppAccent.orangeA;
    }
  }

  static Color _secondaryFor(AppThemeChoice choice) {
    switch (choice) {
      case AppThemeChoice.luxlunch:
        return AppAccent.orangeB;
      case AppThemeChoice.ocean:
        return const Color(0xFF3CAAFF);
      case AppThemeChoice.sunset:
        return const Color(0xFFFF5A00);
      case AppThemeChoice.forest:
        return const Color(0xFF2DFF9A);
      case AppThemeChoice.contrast:
        return const Color(0xFFFFFFFF);
      case AppThemeChoice.light:
        return const Color(0xFF111111);
      case AppThemeChoice.dark:
        return AppAccent.orangeB;
    }
  }

  static BoxDecoration backgroundGradient() {
    return const BoxDecoration(
      gradient: RadialGradient(
        center: Alignment(0.35, -0.75),
        radius: 1.15,
        colors: [
          Color(0x1AFFC06B),
          Color(0x1600B6FF),
          _bg,
        ],
        stops: [0.0, 0.55, 1.0],
      ),
    );
  }

  static BoxDecoration glassCardDecoration(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Colors.white.withValues(alpha: 0.10),
          Colors.white.withValues(alpha: 0.05),
        ],
      ),
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: scheme.outline.withValues(alpha: 0.9)),
    );
  }
}
