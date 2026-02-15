import 'package:flutter/widgets.dart';

enum AppLanguage {
  en,
  zh,
}

extension AppLanguageX on AppLanguage {
  Locale get locale {
    switch (this) {
      case AppLanguage.en:
        return const Locale('en');
      case AppLanguage.zh:
        return const Locale('zh');
    }
  }

  String get code {
    switch (this) {
      case AppLanguage.en:
        return 'en';
      case AppLanguage.zh:
        return 'zh';
    }
  }

  static AppLanguage fromCode(String? raw, {AppLanguage fallback = AppLanguage.en}) {
    switch ((raw ?? '').toLowerCase()) {
      case 'zh':
      case 'zh-cn':
      case 'zh-hans':
        return AppLanguage.zh;
      case 'en':
      case 'en-us':
        return AppLanguage.en;
      default:
        return fallback;
    }
  }
}
