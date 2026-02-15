import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/settings/app_language.dart';
import '../../core/settings/app_theme_choice.dart';
import '../../core/settings/settings_controller.dart';
import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../../ui/style/app_stage.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final settings = ref.watch(settingsControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n?.settingsTitle ?? 'Settings'),
      ),
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: settings.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Failed to load settings: $e')),
              data: (s) {
                return AppStage(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        l10n?.appearanceTitle ?? 'Appearance',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      _LabeledRow(
                        label: l10n?.themeTitle ?? 'Theme',
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<AppThemeChoice>(
                            value: s.theme,
                            isExpanded: true,
                            items: AppThemeChoice.values
                                .map(
                                  (t) => DropdownMenuItem(
                                    value: t,
                                    child: Text(_themeLabel(t)),
                                  ),
                                )
                                .toList(),
                            onChanged: (next) {
                              if (next == null) return;
                              ref.read(settingsControllerProvider.notifier).setTheme(next);
                            },
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      _LabeledRow(
                        label: l10n?.languageTitle ?? 'Language',
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<AppLanguage>(
                            value: s.language,
                            isExpanded: true,
                            items: AppLanguage.values
                                .map(
                                  (lang) => DropdownMenuItem(
                                    value: lang,
                                    child: Text(_languageLabel(lang)),
                                  ),
                                )
                                .toList(),
                            onChanged: (next) {
                              if (next == null) return;
                              ref.read(settingsControllerProvider.notifier).setLanguage(next);
                            },
                          ),
                        ),
                      ),
                      const Spacer(),
                      Text(
                        'Host policy note: use user-api.local for mobile/user calls.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context)
                            .textTheme
                            .bodyLarge
                            ?.copyWith(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.55)),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _LabeledRow extends StatelessWidget {
  final String label;
  final Widget child;

  const _LabeledRow({required this.label, required this.child});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: Colors.white.withValues(alpha: 0.06),
        border: Border.all(color: scheme.outline.withValues(alpha: 0.9)),
      ),
      child: Row(
        children: [
          Expanded(
            flex: 4,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(flex: 5, child: child),
        ],
      ),
    );
  }
}

String _themeLabel(AppThemeChoice t) {
  switch (t) {
    case AppThemeChoice.luxlunch:
      return 'Signature';
    case AppThemeChoice.light:
      return 'Light';
    case AppThemeChoice.dark:
      return 'Dark';
    case AppThemeChoice.ocean:
      return 'Ocean';
    case AppThemeChoice.sunset:
      return 'Sunset';
    case AppThemeChoice.forest:
      return 'Forest';
    case AppThemeChoice.contrast:
      return 'Contrast';
  }
}

String _languageLabel(AppLanguage lang) {
  switch (lang) {
    case AppLanguage.en:
      return 'English';
    case AppLanguage.zh:
      return '中文';
  }
}
