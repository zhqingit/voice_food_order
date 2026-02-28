import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../gen_l10n/app_localizations.dart';
import '../../ui/style/app_background.dart';
import '../../ui/style/app_stage.dart';
import '../settings/settings_screen.dart';
import 'auth_controller.dart';

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
        setState(() {
          _tabIndex = _tabController.index;
        });
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
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        l10n?.appTitle ?? 'Food Order',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                    ),
                    IconButton(
                      tooltip: l10n?.settingsTitle ?? 'Settings',
                      onPressed: () {
                        Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
                      },
                      icon: const Icon(Icons.settings_outlined),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  l10n?.authTitle ?? 'Sign in',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.9)),
                ),
                const SizedBox(height: 4),
                Text(
                  'Sign in to continue, or try guest mode.',
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
                      TabBar(
                        controller: _tabController,
                        tabs: [
                          Tab(text: l10n?.login ?? 'Login'),
                          Tab(text: l10n?.signup ?? 'Sign up'),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (isGuest) ...[
                        Text(
                          'Guest mode enabled (navigation comes next).',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.primary,
                            fontWeight: FontWeight.w600,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 8),
                      ],
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 200),
                        child: _tabIndex == 0
                            ? _AuthForm(
                                key: const ValueKey('login'),
                                title: l10n?.login ?? 'Login',
                                emailLabel: l10n?.email ?? 'Email',
                                passwordLabel: l10n?.password ?? 'Password',
                                emailController: _loginEmail,
                                passwordController: _loginPassword,
                                isLoading: isLoading,
                                message: message,
                                onSubmit: () async {
                                  await ref
                                      .read(authControllerProvider.notifier)
                                      .login(_loginEmail.text.trim(), _loginPassword.text);
                                },
                              )
                            : _AuthForm(
                                key: const ValueKey('signup'),
                                title: l10n?.signup ?? 'Sign up',
                                emailLabel: l10n?.email ?? 'Email',
                                passwordLabel: l10n?.password ?? 'Password',
                                emailController: _signupEmail,
                                passwordController: _signupPassword,
                                isLoading: isLoading,
                                message: message,
                                onSubmit: () async {
                                  await ref
                                      .read(authControllerProvider.notifier)
                                      .signup(_signupEmail.text.trim(), _signupPassword.text);
                                },
                              ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: isLoading
                      ? null
                      : () async {
                          await ref.read(authControllerProvider.notifier).continueAsGuest();
                        },
                  icon: const Icon(Icons.person_outline),
                  label: Text(l10n?.continueAsGuest ?? 'Continue as Guest'),
                ),
                const SizedBox(height: 16),
                Text(
                  'Tip: use a user-portal API host when testing auth.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context)
                      .textTheme
                      .bodyLarge
                      ?.copyWith(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _AuthForm extends StatelessWidget {
  final String title;
  final String emailLabel;
  final String passwordLabel;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final bool isLoading;
  final String? message;
  final Future<void> Function() onSubmit;

  const _AuthForm({
    super.key,
    required this.title,
    required this.emailLabel,
    required this.passwordLabel,
    required this.emailController,
    required this.passwordController,
    required this.isLoading,
    required this.message,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (message != null) ...[
            Text(message!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 12),
          ],
          TextField(
            controller: emailController,
            keyboardType: TextInputType.emailAddress,
            decoration: InputDecoration(labelText: emailLabel),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: passwordController,
            obscureText: true,
            decoration: InputDecoration(labelText: passwordLabel),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: isLoading ? null : onSubmit,
            child: isLoading
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Theme.of(context).colorScheme.onPrimary,
                    ),
                  )
                : Text(title),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
