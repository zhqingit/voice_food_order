import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../auth/auth_controller.dart';

/// Provider that fetches the current user's profile from /user/me.
final _userProfileProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final dio = ref.watch(apiClientProvider).dio;
  final res = await dio.get<Map<String, dynamic>>('/user/me');
  return res.data!;
});

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;

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
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            children: [
              _ProfileSection(),
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
              const SizedBox(height: 20),
              _AccountSection(),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProfileSection extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final isGuest = authState is Guest;
    final profile = ref.watch(_userProfileProvider);

    return _SectionCard(
      children: [
        const _SectionHeader(icon: Icons.person_outline_rounded, title: 'Profile'),
        const SizedBox(height: 20),
        if (isGuest)
          _GuestProfile()
        else
          profile.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            ),
            error: (_, __) => const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(child: Text('Failed to load profile', style: TextStyle(color: Color(0xFF8A8A8A)))),
            ),
            data: (data) => _UserProfile(data: data),
          ),
      ],
    );
  }
}

class _GuestProfile extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: const Color(0xFFF5F5F5),
            shape: BoxShape.circle,
            border: Border.all(color: Colors.grey.withValues(alpha: 0.2)),
          ),
          child: const Icon(Icons.person_outline, size: 32, color: Color(0xFF8A8A8A)),
        ),
        const SizedBox(height: 12),
        const Text('Guest', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Color(0xFF2D2D2D))),
        const SizedBox(height: 4),
        const Text(
          'Sign in to save your orders and preferences',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 13, color: Color(0xFF8A8A8A)),
        ),
      ],
    );
  }
}

class _UserProfile extends StatelessWidget {
  final Map<String, dynamic> data;
  const _UserProfile({required this.data});

  @override
  Widget build(BuildContext context) {
    final email = data['email'] as String? ?? '';
    final createdAt = data['created_at'] as String? ?? '';
    final initial = email.isNotEmpty ? email[0].toUpperCase() : '?';

    String memberSince = '';
    if (createdAt.isNotEmpty) {
      final dt = DateTime.tryParse(createdAt);
      if (dt != null) {
        memberSince = '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
      }
    }

    return Column(
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: const BoxDecoration(
            color: Color(0xFFFF9F1C),
            shape: BoxShape.circle,
          ),
          child: Center(
            child: Text(initial, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: Colors.white)),
          ),
        ),
        const SizedBox(height: 16),
        _AboutRow(label: 'Email', value: email),
        const SizedBox(height: 10),
        if (memberSince.isNotEmpty) _AboutRow(label: 'Member since', value: memberSince),
      ],
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
        Flexible(
          child: Text(
            value,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFF3D3D3D)),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _AccountSection extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final isGuest = authState is Guest;

    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: () async {
          await ref.read(authControllerProvider.notifier).logoutCurrent();
          if (context.mounted) {
            Navigator.of(context).popUntil((route) => route.isFirst);
          }
        },
        icon: Icon(isGuest ? Icons.login_rounded : Icons.logout_rounded, size: 20),
        label: Text(isGuest ? 'Sign In' : 'Sign Out'),
        style: ElevatedButton.styleFrom(
          backgroundColor: isGuest ? const Color(0xFFFF9F1C) : const Color(0xFFF5F5F5),
          foregroundColor: isGuest ? Colors.white : const Color(0xFF3D3D3D),
          elevation: isGuest ? 2 : 0,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
