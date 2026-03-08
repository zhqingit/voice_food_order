import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../core/settings/app_language.dart';
import '../../core/settings/settings_controller.dart';
import '../../data/store_models.dart';
import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../settings/settings_screen.dart';
import '../voice/voice_order_screen.dart';

const Color _warmOrangeStart = Color(0xFFFF8A2A);
const Color _warmOrangeEnd = Color(0xFFFFB15A);
const Color _warmBrown = Color(0xFF2E241A);
const Color _warmBrownLight = Color(0xFF6D5D4B);
const Color _cardBg = Color(0xFFFFFBF5);
const Color _searchFill = Color(0xFFF5EDE3);
const Color _chipBg = Color(0xFFFFF3E0);
const Color _chipBorder = Color(0xFFFFCC80);
const Color _greenDot = Color(0xFF66BB6A);
const Color _redDot = Color(0xFFEF5350);
const Color _grayDot = Color(0xFF9E9E9E);

class StoresScreen extends ConsumerStatefulWidget {
  const StoresScreen({super.key});

  @override
  ConsumerState<StoresScreen> createState() => _StoresScreenState();
}

class _StoresScreenState extends ConsumerState<StoresScreen> {
  List<StorePublicOut>? _stores;
  bool _loading = true;
  String? _error;

  final _searchController = TextEditingController();
  String _searchQuery = '';

  List<StorePublicOut> get _filteredStores {
    if (_stores == null) return [];
    if (_searchQuery.isEmpty) return _stores!;
    final q = _searchQuery.toLowerCase();
    return _stores!.where((s) => s.name.toLowerCase().contains(q)).toList();
  }

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() => setState(() => _searchQuery = _searchController.text));
    _loadStores();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadStores() async {
    setState(() { _loading = true; _error = null; });
    try {
      final stores = await ref.read(storeRepositoryProvider).listStores();
      if (mounted) setState(() => _stores = stores);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _openVoiceOrder(String storeName, String storeId) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => VoiceOrderScreen(storeName: storeName, storeId: storeId),
    ));
  }

  String _greeting(AppLocalizations l10n) {
    final hour = DateTime.now().hour;
    if (hour < 12) return l10n.goodMorning;
    if (hour < 17) return l10n.goodAfternoon;
    return l10n.goodEvening;
  }

  void _cycleLanguage() {
    final settings = ref.read(settingsControllerProvider).valueOrNull;
    if (settings == null) return;
    final langs = AppLanguage.values;
    final nextIndex = (langs.indexOf(settings.language) + 1) % langs.length;
    ref.read(settingsControllerProvider.notifier).setLanguage(langs[nextIndex]);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final settings = ref.watch(settingsControllerProvider).valueOrNull;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          bottom: false,
          child: RefreshIndicator(
            color: _warmOrangeStart,
            onRefresh: _loadStores,
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
              slivers: [
                // Header
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 12, 12, 0),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${_greeting(l10n)} !',
                                style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: _warmBrown, height: 1.2),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                l10n.pickStore,
                                style: TextStyle(fontSize: 15, color: _warmBrownLight.withValues(alpha: 0.85)),
                              ),
                            ],
                          ),
                        ),
                        // Language switcher button
                        GestureDetector(
                          onTap: _cycleLanguage,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: _searchFill,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: _chipBorder.withValues(alpha: 0.5)),
                            ),
                            child: Text(
                              settings?.language.shortLabel ?? 'EN',
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: _warmBrown),
                            ),
                          ),
                        ),
                        const SizedBox(width: 4),
                        IconButton(
                          tooltip: l10n.settingsTitle,
                          icon: const Icon(Icons.settings_outlined, color: _warmBrown, size: 26),
                          onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen())),
                        ),
                        Container(
                          width: 42, height: 42,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: const LinearGradient(colors: [_warmOrangeStart, _warmOrangeEnd], begin: Alignment.topLeft, end: Alignment.bottomRight),
                            boxShadow: [BoxShadow(color: _warmOrangeStart.withValues(alpha: 0.30), blurRadius: 8, offset: const Offset(0, 3))],
                          ),
                          child: const Icon(Icons.person_rounded, color: Colors.white, size: 22),
                        ),
                        const SizedBox(width: 8),
                      ],
                    ),
                  ),
                ),

                // Search
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
                    child: TextField(
                      controller: _searchController,
                      style: const TextStyle(fontSize: 15, color: _warmBrown),
                      cursorColor: _warmOrangeStart,
                      decoration: InputDecoration(
                        hintText: l10n.searchRestaurants,
                        hintStyle: TextStyle(color: _warmBrownLight.withValues(alpha: 0.55)),
                        prefixIcon: Icon(Icons.search_rounded, color: _warmBrownLight.withValues(alpha: 0.6)),
                        suffixIcon: _searchQuery.isNotEmpty
                            ? IconButton(icon: Icon(Icons.clear_rounded, color: _warmBrownLight.withValues(alpha: 0.5)), onPressed: () => _searchController.clear())
                            : null,
                        filled: true,
                        fillColor: _searchFill,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(28), borderSide: BorderSide.none),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(28), borderSide: BorderSide.none),
                        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(28), borderSide: BorderSide(color: _warmOrangeEnd.withValues(alpha: 0.6), width: 1.5)),
                      ),
                    ),
                  ),
                ),

                // Section label
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(22, 14, 22, 8),
                    child: Text(l10n.nearbyRestaurants, style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: _warmBrown.withValues(alpha: 0.85))),
                  ),
                ),

                // Content
                if (_loading)
                  const SliverFillRemaining(hasScrollBody: false, child: Center(child: CircularProgressIndicator(color: _warmOrangeStart)))
                else if (_error != null)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 72, height: 72,
                              decoration: BoxDecoration(color: const Color(0xFFFBE9E7), shape: BoxShape.circle, border: Border.all(color: const Color(0xFFFFCCBC), width: 1.5)),
                              child: const Icon(Icons.wifi_off_rounded, size: 32, color: Color(0xFFE64A19)),
                            ),
                            const SizedBox(height: 20),
                            Text(l10n.somethingWentWrong, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: _warmBrown)),
                            const SizedBox(height: 8),
                            Text(_error!, textAlign: TextAlign.center, maxLines: 3, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 13, color: _warmBrownLight.withValues(alpha: 0.7))),
                            const SizedBox(height: 24),
                            _GradientButton(label: l10n.tryAgain, icon: Icons.refresh_rounded, onPressed: _loadStores),
                          ],
                        ),
                      ),
                    ),
                  )
                else ...[
                  if (_filteredStores.isNotEmpty)
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                      sliver: SliverGrid(
                        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          mainAxisSpacing: 14,
                          crossAxisSpacing: 14,
                          childAspectRatio: 1.0,
                        ),
                        delegate: SliverChildBuilderDelegate(
                          (context, index) => _StoreCard(store: _filteredStores[index], onTap: _openVoiceOrder),
                          childCount: _filteredStores.length,
                        ),
                      ),
                    )
                  else
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 80, height: 80,
                              decoration: BoxDecoration(color: _chipBg, shape: BoxShape.circle, border: Border.all(color: _chipBorder, width: 1.5)),
                              child: Icon(_searchQuery.isNotEmpty ? Icons.search_off_rounded : Icons.storefront_outlined, size: 36, color: _warmOrangeStart),
                            ),
                            const SizedBox(height: 20),
                            Text(
                              _searchQuery.isNotEmpty ? l10n.noMatchesFound : l10n.noRestaurantsYet,
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: _warmBrown),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
                const SliverToBoxAdapter(child: SizedBox(height: 32)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StoreCard extends StatelessWidget {
  final StorePublicOut store;
  final void Function(String name, String id) onTap;

  const _StoreCard({required this.store, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Container(
      decoration: BoxDecoration(
        color: _cardBg,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: _warmBrownLight.withValues(alpha: 0.08), blurRadius: 16, offset: const Offset(0, 6)),
          BoxShadow(color: _warmBrownLight.withValues(alpha: 0.04), blurRadius: 4, offset: const Offset(0, 2)),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          splashColor: _warmOrangeEnd.withValues(alpha: 0.08),
          onTap: () => onTap(store.name, store.id),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Top: open/closed status + mic icon
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _StatusBadge(isOpen: store.isCurrentlyOpen),
                    Icon(Icons.mic_rounded, size: 18, color: _warmOrangeStart.withValues(alpha: 0.6)),
                  ],
                ),
                // Center: store icon + name
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    store.logoUrl != null
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(14),
                            child: Image.network(
                              store.logoUrl!,
                              width: 48,
                              height: 48,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => Container(
                                width: 48,
                                height: 48,
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: [_warmOrangeStart.withValues(alpha: 0.15), _warmOrangeEnd.withValues(alpha: 0.10)],
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                  ),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: const Icon(Icons.restaurant_rounded, size: 24, color: _warmOrangeStart),
                              ),
                            ),
                          )
                        : Container(
                            width: 48,
                            height: 48,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [_warmOrangeStart.withValues(alpha: 0.15), _warmOrangeEnd.withValues(alpha: 0.10)],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: const Icon(Icons.restaurant_rounded, size: 24, color: _warmOrangeStart),
                          ),
                    const SizedBox(height: 10),
                    Text(
                      store.name,
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: _warmBrown, height: 1.2),
                    ),
                  ],
                ),
                // Bottom: service tags + today's hours
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (store.allowPickup) _ServiceChip(label: l10n.pickup, icon: Icons.storefront_outlined),
                        if (store.allowPickup && store.allowDelivery) const SizedBox(width: 6),
                        if (store.allowDelivery) _ServiceChip(label: l10n.delivery, icon: Icons.delivery_dining_outlined),
                      ],
                    ),
                    if (store.todayHoursLabel != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        store.todayHoursLabel!,
                        style: TextStyle(fontSize: 9, color: _warmBrownLight.withValues(alpha: 0.6)),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final bool? isOpen; // null = unknown (no hours set)

  const _StatusBadge({required this.isOpen});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final Color dotColor;
    final Color textColor;
    final String label;

    if (isOpen == null) {
      dotColor = _grayDot;
      textColor = const Color(0xFF757575);
      label = '--';
    } else if (isOpen!) {
      dotColor = _greenDot;
      textColor = const Color(0xFF2E7D32);
      label = l10n.storeOpen;
    } else {
      dotColor = _redDot;
      textColor = const Color(0xFFC62828);
      label = l10n.storeClosed;
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 7, height: 7, decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle)),
        const SizedBox(width: 5),
        Text(label, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: textColor)),
      ],
    );
  }
}

class _ServiceChip extends StatelessWidget {
  final String label;
  final IconData icon;

  const _ServiceChip({required this.label, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(color: _chipBg, borderRadius: BorderRadius.circular(8), border: Border.all(color: _chipBorder)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: _warmOrangeStart),
          const SizedBox(width: 3),
          Text(label, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w500, color: _warmOrangeStart)),
        ],
      ),
    );
  }
}

class _GradientButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onPressed;

  const _GradientButton({required this.label, required this.icon, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: Container(
        height: 48,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: const LinearGradient(colors: [_warmOrangeStart, _warmOrangeEnd], begin: Alignment.centerLeft, end: Alignment.centerRight),
          boxShadow: [BoxShadow(color: _warmOrangeStart.withValues(alpha: 0.30), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(width: 20),
            Icon(icon, color: Colors.white, size: 20),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600, letterSpacing: 0.3)),
            const SizedBox(width: 20),
          ],
        ),
      ),
    );
  }
}
