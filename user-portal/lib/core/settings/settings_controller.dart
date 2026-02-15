import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app_language.dart';
import 'app_settings.dart';
import 'app_theme_choice.dart';

const _kThemeKey = 'user-portal.theme';
const _kLanguageKey = 'user-portal.language';

final settingsControllerProvider = AsyncNotifierProvider<SettingsController, AppSettings>(
  SettingsController.new,
);

class SettingsController extends AsyncNotifier<AppSettings> {
  @override
  Future<AppSettings> build() async {
    final prefs = await SharedPreferences.getInstance();

    final theme = AppThemeChoiceX.fromCode(prefs.getString(_kThemeKey));
    final language = AppLanguageX.fromCode(prefs.getString(_kLanguageKey), fallback: AppLanguage.en);

    // Default language is en (explicit requirement).
    return AppSettings(theme: theme, language: language);
  }

  Future<void> setTheme(AppThemeChoice theme) async {
    final current = state.valueOrNull;
    if (current == null) return;

    state = AsyncValue.data(current.copyWith(theme: theme));

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kThemeKey, theme.code);
  }

  Future<void> setLanguage(AppLanguage language) async {
    final current = state.valueOrNull;
    if (current == null) return;

    state = AsyncValue.data(current.copyWith(language: language));

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLanguageKey, language.code);
  }
}
