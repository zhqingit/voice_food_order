import 'package:flutter/widgets.dart';

enum AppLanguage {
  en,
  zh,
  es,
}

extension AppLanguageX on AppLanguage {
  Locale get locale {
    switch (this) {
      case AppLanguage.en:
        return const Locale('en');
      case AppLanguage.zh:
        return const Locale('zh');
      case AppLanguage.es:
        return const Locale('es');
    }
  }

  String get code {
    switch (this) {
      case AppLanguage.en:
        return 'en';
      case AppLanguage.zh:
        return 'zh';
      case AppLanguage.es:
        return 'es';
    }
  }

  /// Short display label for the language switcher button.
  String get shortLabel {
    switch (this) {
      case AppLanguage.en:
        return 'EN';
      case AppLanguage.zh:
        return '中文';
      case AppLanguage.es:
        return 'ES';
    }
  }

  static AppLanguage fromCode(String? raw, {AppLanguage fallback = AppLanguage.en}) {
    switch ((raw ?? '').toLowerCase()) {
      case 'zh':
      case 'zh-cn':
      case 'zh-hans':
        return AppLanguage.zh;
      case 'es':
      case 'es-es':
        return AppLanguage.es;
      case 'en':
      case 'en-us':
        return AppLanguage.en;
      default:
        return fallback;
    }
  }
}
