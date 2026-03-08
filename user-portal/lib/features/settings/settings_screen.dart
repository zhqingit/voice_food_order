import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/settings/app_language.dart';
import '../../core/settings/app_theme_choice.dart';
import '../../core/settings/settings_controller.dart';
import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  static const _themeColors = <AppThemeChoice, Color>{
    AppThemeChoice.luxlunch: Color(0xFFFFB15A),
    AppThemeChoice.light: Color(0xFFEAEFF7),
    AppThemeChoice.dark: Color(0xFFFF8A2A),
    AppThemeChoice.ocean: Color(0xFF78B4FF),
    AppThemeChoice.sunset: Color(0xFFFF78DC),
    AppThemeChoice.forest: Color(0xFF78FFBE),
    AppThemeChoice.contrast: Color(0xFFFFFFFF),
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final settings = ref.watch(settingsControllerProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.9),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.08),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: const Icon(Icons.arrow_back_ios_new, size: 18, color: Color(0xFF3D3D3D)),
          ),
          onPressed: () => Navigator.of(context).pop(),
        ),
        centerTitle: true,
        title: Text(
          l10n.settingsTitle,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: Color(0xFF2D2D2D)),
        ),
      ),
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          child: settings.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('$e')),
            data: (s) {
              return ListView(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                children: [
                  _SectionCard(
                    children: [
                      _SectionHeader(icon: Icons.palette_outlined, title: l10n.appearanceTitle),
                      const SizedBox(height: 20),
                      Text(
                        l10n.themeTitle,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF5A5A5A)),
                      ),
                      const SizedBox(height: 14),
                      _ThemeGrid(
                        selected: s.theme,
                        onSelected: (next) => ref.read(settingsControllerProvider.notifier).setTheme(next),
                        themeColors: _themeColors,
                      ),
                      const SizedBox(height: 28),
                      Divider(color: Colors.grey.withValues(alpha: 0.15), height: 1),
                      const SizedBox(height: 20),
                      Text(
                        l10n.languageTitle,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF5A5A5A)),
                      ),
                      const SizedBox(height: 14),
                      _LanguageToggle(
                        selected: s.language,
                        onSelected: (next) => ref.read(settingsControllerProvider.notifier).setLanguage(next),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  _SectionCard(
                    children: [
                      _SectionHeader(icon: Icons.info_outline_rounded, title: l10n.about),
                      const SizedBox(height: 16),
                      _AboutRow(label: l10n.appName, value: l10n.appNameValue),
                      const SizedBox(height: 10),
                      _AboutRow(label: l10n.version, value: '1.0.0'),
                    ],
                  ),
                  const SizedBox(height: 32),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final List<Widget> children;
  const _SectionCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 20, offset: const Offset(0, 4)),
          BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 6, offset: const Offset(0, 1)),
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  const _SectionHeader({required this.icon, required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFFFFB15A).withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 20, color: const Color(0xFFFF9F1C)),
        ),
        const SizedBox(width: 12),
        Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Color(0xFF2D2D2D))),
      ],
    );
  }
}

class _ThemeGrid extends StatelessWidget {
  final AppThemeChoice selected;
  final ValueChanged<AppThemeChoice> onSelected;
  final Map<AppThemeChoice, Color> themeColors;

  const _ThemeGrid({required this.selected, required this.onSelected, required this.themeColors});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    String themeLabel(AppThemeChoice t) {
      switch (t) {
        case AppThemeChoice.luxlunch: return l10n.themeSignature;
        case AppThemeChoice.light: return l10n.themeLight;
        case AppThemeChoice.dark: return l10n.themeDark;
        case AppThemeChoice.ocean: return l10n.themeOcean;
        case AppThemeChoice.sunset: return l10n.themeSunset;
        case AppThemeChoice.forest: return l10n.themeForest;
        case AppThemeChoice.contrast: return l10n.themeContrast;
      }
    }

    return Wrap(
      spacing: 16,
      runSpacing: 16,
      children: AppThemeChoice.values.map((theme) {
        final isSelected = theme == selected;
        final color = themeColors[theme] ?? Colors.grey;
        return GestureDetector(
          onTap: () => onSelected(theme),
          child: SizedBox(
            width: 72,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeInOut,
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isSelected ? const Color(0xFFFF9F1C) : Colors.grey.withValues(alpha: 0.25),
                      width: isSelected ? 3 : 1.5,
                    ),
                    boxShadow: isSelected
                        ? [BoxShadow(color: color.withValues(alpha: 0.4), blurRadius: 12, offset: const Offset(0, 3))]
                        : [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 4, offset: const Offset(0, 2))],
                  ),
                  child: isSelected
                      ? Center(
                          child: Icon(
                            Icons.check_rounded,
                            size: 24,
                            color: color.computeLuminance() > 0.5 ? const Color(0xFF2D2D2D) : Colors.white,
                          ),
                        )
                      : null,
                ),
                const SizedBox(height: 8),
                Text(
                  themeLabel(theme),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                    color: isSelected ? const Color(0xFF2D2D2D) : const Color(0xFF8A8A8A),
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _LanguageToggle extends StatelessWidget {
  final AppLanguage selected;
  final ValueChanged<AppLanguage> onSelected;

  const _LanguageToggle({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(color: const Color(0xFFF5F5F5), borderRadius: BorderRadius.circular(14)),
      padding: const EdgeInsets.all(4),
      child: Row(
        children: AppLanguage.values.map((lang) {
          final isActive = lang == selected;
          return Expanded(
            child: GestureDetector(
              onTap: () => onSelected(lang),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeInOut,
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: isActive ? Colors.white : Colors.transparent,
                  borderRadius: BorderRadius.circular(11),
                  boxShadow: isActive
                      ? [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 8, offset: const Offset(0, 2))]
                      : null,
                ),
                child: Center(
                  child: Text(
                    lang.shortLabel,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
                      color: isActive ? const Color(0xFF2D2D2D) : const Color(0xFF9A9A9A),
                    ),
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _AboutRow extends StatelessWidget {
  final String label;
  final String value;
  const _AboutRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: Color(0xFF8A8A8A))),
        Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFF3D3D3D))),
      ],
    );
  }
}
