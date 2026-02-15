import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:liquid_glass_flutter/liquid_glass_flutter.dart';
import '../gen_l10n/app_localizations.dart';

import '../core/app_theme.dart';
import '../core/settings/app_settings.dart';
import '../core/settings/app_language.dart';
import '../core/settings/app_theme_choice.dart';
import '../core/settings/settings_controller.dart';
import '../features/auth/auth_controller.dart';
import '../features/auth/auth_screen.dart';
import '../features/store/stores_screen.dart';

class AppRoot extends ConsumerStatefulWidget {
  const AppRoot({super.key});

  @override
  ConsumerState<AppRoot> createState() => _AppRootState();
}

class _AppRootState extends ConsumerState<AppRoot> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // After first frame, attempt a proactive refresh if needed.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authControllerProvider.notifier).refreshIfNeeded();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      ref.read(authControllerProvider.notifier).refreshIfNeeded();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final settings = ref.watch(settingsControllerProvider);

    return settings.when(
      loading: () => const MaterialApp(home: Scaffold(body: Center(child: CircularProgressIndicator()))),
      error: (_, __) => const MaterialApp(home: Scaffold(body: Center(child: Text('Failed to load settings')))),
      data: (AppSettings s) {
        final glassThemeData = null;
        final glassThemeName = s.theme.glassThemeName;

        return GlassTheme(
          theme: glassThemeName,
          data: glassThemeData,
          child: MaterialApp(
            onGenerateTitle: (ctx) => AppLocalizations.of(ctx)?.appTitle ?? 'Food Order',
            theme: AppTheme.materialFor(s.theme),
            darkTheme: AppTheme.materialFor(s.theme),
            themeMode: s.theme == AppThemeChoice.luxlunch ? ThemeMode.light : ThemeMode.dark,
            locale: s.language.locale,
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            home: switch (authState) {
              Authenticated() => const StoresScreen(),
              Guest() => const StoresScreen(),
              Unauthenticated() => const AuthScreen(),
              _ => const Scaffold(body: Center(child: CircularProgressIndicator())),
            },
          ),
        );
      },
    );
  }
}
