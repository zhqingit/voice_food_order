import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../settings/settings_screen.dart';
import 'auth_controller.dart';

const _kPrimaryStart = Color(0xFFFF8A2A);
const _kPrimaryEnd = Color(0xFFFFB15A);
const _kTextDark = Color(0xFF2E241A);
const _kTextMuted = Color(0xFF6D5D4B);
const _kCardColor = Color(0xF2FFFFFF);
const _kErrorBg = Color(0xFFFFF0E6);
const _kErrorFg = Color(0xFFCC4B00);

const _kCardRadius = 24.0;
const _kFieldRadius = 14.0;
const _kButtonRadius = 16.0;

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> with TickerProviderStateMixin {
  late final TabController _tabController;
  int _tabIndex = 0;

  final _loginEmail = TextEditingController();
  final _loginPassword = TextEditingController();
  final _signupEmail = TextEditingController();
  final _signupPassword = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging && _tabIndex != _tabController.index) {
        setState(() => _tabIndex = _tabController.index);
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginEmail.dispose();
    _loginPassword.dispose();
    _signupEmail.dispose();
    _signupPassword.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(authControllerProvider);
    final isLoading = state is AuthLoading;
    final message = state is Unauthenticated ? state.message : null;
    final isGuest = state is Guest;

    return Scaffold(
      body: Container(
        decoration: AppBackground.decoration(),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: IconButton(
                    tooltip: l10n?.settingsTitle ?? 'Settings',
                    onPressed: () {
                      Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
                    },
                    icon: const Icon(Icons.settings_outlined, color: _kTextMuted, size: 26),
                  ),
                ),
                const SizedBox(height: 12),

                // Hero logo
                Center(
                  child: Image.asset(
                    'assets/logo.png',
                    width: 160,
                    height: 160,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  l10n?.authTitle ?? 'Sign in to continue',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500, color: _kTextMuted),
                ),
                const SizedBox(height: 32),

                // Card
                Container(
                  decoration: BoxDecoration(
                    color: _kCardColor,
                    borderRadius: BorderRadius.circular(_kCardRadius),
                    boxShadow: [
                      BoxShadow(color: const Color(0xFF8B7355).withValues(alpha: 0.08), blurRadius: 32, offset: const Offset(0, 12)),
                      BoxShadow(color: const Color(0xFF8B7355).withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 2)),
                    ],
                  ),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _PillTabBar(
                          controller: _tabController,
                          labels: [l10n?.login ?? 'Login', l10n?.signup ?? 'Sign up'],
                          selectedIndex: _tabIndex,
                        ),
                        const SizedBox(height: 20),
                        if (isGuest) ...[
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            decoration: BoxDecoration(
                              color: _kPrimaryEnd.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.check_circle_rounded, color: _kPrimaryStart, size: 20),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(l10n?.guestModeEnabled ?? 'Guest mode enabled.', style: const TextStyle(color: _kPrimaryStart, fontWeight: FontWeight.w600, fontSize: 13)),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 14),
                        ],
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 250),
                          switchInCurve: Curves.easeOut,
                          switchOutCurve: Curves.easeIn,
                          child: _tabIndex == 0
                              ? _AuthForm(
                                  key: const ValueKey('login'),
                                  buttonLabel: l10n?.login ?? 'Login',
                                  emailLabel: l10n?.email ?? 'Email',
                                  passwordLabel: l10n?.password ?? 'Password',
                                  emailController: _loginEmail,
                                  passwordController: _loginPassword,
                                  isLoading: isLoading,
                                  message: message,
                                  onSubmit: () async {
                                    await ref.read(authControllerProvider.notifier).login(_loginEmail.text.trim(), _loginPassword.text);
                                  },
                                )
                              : _AuthForm(
                                  key: const ValueKey('signup'),
                                  buttonLabel: l10n?.signup ?? 'Sign up',
                                  emailLabel: l10n?.email ?? 'Email',
                                  passwordLabel: l10n?.password ?? 'Password',
                                  emailController: _signupEmail,
                                  passwordController: _signupPassword,
                                  isLoading: isLoading,
                                  message: message,
                                  onSubmit: () async {
                                    await ref.read(authControllerProvider.notifier).signup(_signupEmail.text.trim(), _signupPassword.text);
                                  },
                                ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Center(
                  child: TextButton(
                    onPressed: isLoading
                        ? null
                        : () async {
                            await ref.read(authControllerProvider.notifier).continueAsGuest();
                          },
                    style: TextButton.styleFrom(
                      foregroundColor: _kTextMuted,
                      textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    ),
                    child: Text(l10n?.continueAsGuest ?? 'Continue as Guest'),
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PillTabBar extends StatelessWidget {
  final TabController controller;
  final List<String> labels;
  final int selectedIndex;

  const _PillTabBar({required this.controller, required this.labels, required this.selectedIndex});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 46,
      decoration: BoxDecoration(color: const Color(0xFFF3EDE4), borderRadius: BorderRadius.circular(14)),
      padding: const EdgeInsets.all(4),
      child: Row(
        children: List.generate(labels.length, (i) {
          final selected = selectedIndex == i;
          return Expanded(
            child: GestureDetector(
              onTap: () => controller.animateTo(i),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeInOut,
                decoration: BoxDecoration(
                  color: selected ? Colors.white : Colors.transparent,
                  borderRadius: BorderRadius.circular(11),
                  boxShadow: selected
                      ? [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 8, offset: const Offset(0, 2))]
                      : [],
                ),
                alignment: Alignment.center,
                child: Text(
                  labels[i],
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: selected ? _kTextDark : _kTextMuted,
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _AuthForm extends StatefulWidget {
  final String buttonLabel;
  final String emailLabel;
  final String passwordLabel;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final bool isLoading;
  final String? message;
  final Future<void> Function() onSubmit;

  const _AuthForm({
    super.key,
    required this.buttonLabel,
    required this.emailLabel,
    required this.passwordLabel,
    required this.emailController,
    required this.passwordController,
    required this.isLoading,
    required this.message,
    required this.onSubmit,
  });

  @override
  State<_AuthForm> createState() => _AuthFormState();
}

class _AuthFormState extends State<_AuthForm> {
  bool _obscurePassword = true;

  InputDecoration _fieldDecoration({required String label, required IconData icon, Widget? suffixIcon}) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: _kTextMuted, fontWeight: FontWeight.w500, fontSize: 14),
      prefixIcon: Icon(icon, color: _kTextMuted, size: 20),
      suffixIcon: suffixIcon,
      filled: true,
      fillColor: const Color(0xFFFAF7F2),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(_kFieldRadius), borderSide: BorderSide.none),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(_kFieldRadius), borderSide: const BorderSide(color: Color(0xFFE8E0D4))),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(_kFieldRadius), borderSide: const BorderSide(color: _kPrimaryStart, width: 1.5)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.message != null) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(color: _kErrorBg, borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded, color: _kErrorFg, size: 18),
                const SizedBox(width: 8),
                Expanded(child: Text(widget.message!, style: const TextStyle(color: _kErrorFg, fontSize: 13, fontWeight: FontWeight.w500))),
              ],
            ),
          ),
          const SizedBox(height: 14),
        ],
        TextField(
          controller: widget.emailController,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.next,
          style: const TextStyle(color: _kTextDark, fontSize: 15),
          decoration: _fieldDecoration(label: widget.emailLabel, icon: Icons.email_outlined),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: widget.passwordController,
          obscureText: _obscurePassword,
          textInputAction: TextInputAction.done,
          style: const TextStyle(color: _kTextDark, fontSize: 15),
          onSubmitted: (_) {
            if (!widget.isLoading) widget.onSubmit();
          },
          decoration: _fieldDecoration(
            label: widget.passwordLabel,
            icon: Icons.lock_outline_rounded,
            suffixIcon: GestureDetector(
              onTap: () => setState(() => _obscurePassword = !_obscurePassword),
              child: Icon(
                _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                color: _kTextMuted,
                size: 20,
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),
        _GradientButton(label: widget.buttonLabel, isLoading: widget.isLoading, onPressed: widget.isLoading ? null : widget.onSubmit),
      ],
    );
  }
}

class _GradientButton extends StatelessWidget {
  final String label;
  final bool isLoading;
  final VoidCallback? onPressed;

  const _GradientButton({required this.label, required this.isLoading, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 52,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: onPressed != null
                ? [_kPrimaryStart, _kPrimaryEnd]
                : [_kPrimaryStart.withValues(alpha: 0.5), _kPrimaryEnd.withValues(alpha: 0.5)],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(_kButtonRadius),
          boxShadow: onPressed != null
              ? [BoxShadow(color: _kPrimaryStart.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))]
              : [],
        ),
        alignment: Alignment.center,
        child: isLoading
            ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
            : Text(label, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700, letterSpacing: 0.3)),
      ),
    );
  }
}
