import 'app_language.dart';
import 'app_theme_choice.dart';

class AppSettings {
  final AppThemeChoice theme;
  final AppLanguage language;

  const AppSettings({
    required this.theme,
    required this.language,
  });

  AppSettings copyWith({
    AppThemeChoice? theme,
    AppLanguage? language,
  }) {
    return AppSettings(
      theme: theme ?? this.theme,
      language: language ?? this.language,
    );
  }
}
