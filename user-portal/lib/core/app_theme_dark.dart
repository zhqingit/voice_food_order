import 'package:flutter/material.dart';

class AppTheme {
  // Palette approximated from the provided reference image.
  // Intentionally dark navy background + cyan/purple neon accents.
  static const _bg = Color(0xFF050816);
  static const _surface = Color(0xFF0B1028);
  static const _surface2 = Color(0xFF101A3A);

  static const _cyan = Color(0xFF37E6FF);
  static const _purple = Color(0xFF9B5CFF);
  static const _magenta = Color(0xFFFF4FD8);

  static const _outline = Color(0xFF2A3B6A);
  static const _text = Color(0xFFEAF2FF);

  static ThemeData dark() {
    final scheme = const ColorScheme(
      brightness: Brightness.dark,
      primary: _cyan,
      onPrimary: Color(0xFF001018),
      secondary: _purple,
      onSecondary: Colors.black,
      tertiary: _magenta,
      onTertiary: Colors.black,
      error: Color(0xFFFF5C6C),
      onError: Colors.black,
      surface: _surface,
      onSurface: _text,
      surfaceContainerHighest: _surface2,
      outline: _outline,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: _bg,
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: scheme.onSurface,
        unselectedLabelColor: scheme.onSurface.withValues(alpha: 0.65),
        indicatorColor: scheme.primary,
        dividerColor: scheme.outline.withValues(alpha: 0.5),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surfaceContainerHighest.withValues(alpha: 0.55),
        hintStyle: TextStyle(color: scheme.onSurface.withValues(alpha: 0.6)),
        labelStyle: TextStyle(color: scheme.onSurface.withValues(alpha: 0.8)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outline.withValues(alpha: 0.7)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outline.withValues(alpha: 0.55)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.primary.withValues(alpha: 0.9), width: 1.6),
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
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: scheme.onSurface,
          side: BorderSide(color: scheme.outline.withValues(alpha: 0.8)),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontSize: 34, fontWeight: FontWeight.w700, height: 1.1),
        headlineMedium: TextStyle(fontSize: 26, fontWeight: FontWeight.w700),
        titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
        bodyLarge: TextStyle(fontSize: 16, height: 1.3),
      ).apply(
        bodyColor: scheme.onSurface,
        displayColor: scheme.onSurface,
      ),
    );
  }

  static BoxDecoration backgroundGradient() {
    return const BoxDecoration(
      gradient: RadialGradient(
        center: Alignment(0.6, -0.8),
        radius: 1.2,
        colors: [
          Color(0x332A7BFF),
          Color(0x221F3CFF),
          Color(0xFF050816),
        ],
        stops: [0.0, 0.45, 1.0],
      ),
    );
  }

  static BoxDecoration glassCardDecoration(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return BoxDecoration(
      color: scheme.surfaceContainerHighest.withValues(alpha: 0.35),
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: scheme.outline.withValues(alpha: 0.55)),
    );
  }
}
