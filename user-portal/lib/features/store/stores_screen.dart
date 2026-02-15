import 'package:flutter/material.dart';

import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../../ui/style/app_stage.dart';
import '../settings/settings_screen.dart';
import '../voice/voice_order_screen.dart';

class StoresScreen extends StatefulWidget {
  const StoresScreen({super.key});

  @override
  State<StoresScreen> createState() => _StoresScreenState();
}

class _StoresScreenState extends State<StoresScreen> {
  final _storeIdController = TextEditingController();

  @override
  void dispose() {
    _storeIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n?.storesTitle ?? 'Stores'),
        actions: [
          IconButton(
            tooltip: l10n?.settingsTitle ?? 'Settings',
            icon: const Icon(Icons.settings_outlined),
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
            },
          ),
        ],
      ),
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  l10n?.pickStore ?? 'Pick a store',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  'Fast pickup • Voice order • Live status',
                  style: Theme.of(context)
                      .textTheme
                      .bodyLarge
                      ?.copyWith(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7)),
                ),
                const SizedBox(height: 16),
                AppStage(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              l10n?.storeName ?? 'Store name',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(999),
                              color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.15),
                              border: Border.all(
                                color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.5),
                              ),
                            ),
                            child: Text(
                              'Open',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyLarge
                                  ?.copyWith(color: Theme.of(context).colorScheme.primary),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'BaoBao • Test store',
                        style: Theme.of(context)
                            .textTheme
                            .bodyLarge
                            ?.copyWith(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.65)),
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: _storeIdController,
                        decoration: InputDecoration(
                          labelText: l10n?.storeId ?? 'Store ID',
                          hintText: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                        ),
                      ),
                      const SizedBox(height: 12),
                      FilledButton(
                        onPressed: () {
                          final storeId = _storeIdController.text.trim();
                          if (storeId.isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Please enter a store UUID first.')),
                            );
                            return;
                          }
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => VoiceOrderScreen(storeName: 'BaoBao', storeId: storeId),
                            ),
                          );
                        },
                        child: Text(l10n?.openVoiceOrder ?? 'Open voice order'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
