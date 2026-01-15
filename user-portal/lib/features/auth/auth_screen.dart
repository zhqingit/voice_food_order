import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_theme.dart';
import 'auth_controller.dart';

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  final _loginEmail = TextEditingController();
  final _loginPassword = TextEditingController();

  final _signupEmail = TextEditingController();
  final _signupPassword = TextEditingController();

  @override
  void dispose() {
    _loginEmail.dispose();
    _loginPassword.dispose();
    _signupEmail.dispose();
    _signupPassword.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authControllerProvider);
    final isLoading = state is AuthLoading;
    final message = state is Unauthenticated ? state.message : null;
    final isGuest = state is Guest;

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        body: Container(
          decoration: AppTheme.backgroundGradient(),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Food Order',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Sign in to continue, or try guest mode.',
                    style: Theme.of(context)
                        .textTheme
                        .bodyLarge
                        ?.copyWith(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7)),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    decoration: AppTheme.glassCardDecoration(context),
                    child: Column(
                      children: [
                        const TabBar(
                          tabs: [
                            Tab(text: 'Login'),
                            Tab(text: 'Sign up'),
                          ],
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          child: AnimatedSize(
                            duration: const Duration(milliseconds: 200),
                            curve: Curves.easeOut,
                            child: Column(
                              children: [
                                if (isGuest) ...[
                                  const SizedBox(height: 12),
                                  Text(
                                    'Guest mode enabled (navigation comes next).',
                                    style: TextStyle(
                                      color: Theme.of(context).colorScheme.primary,
                                      fontWeight: FontWeight.w600,
                                    ),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                                const SizedBox(height: 8),
                                SizedBox(
                                  height: 280,
                                  child: TabBarView(
                                    children: [
                                      _AuthForm(
                                        title: 'Login',
                                        emailController: _loginEmail,
                                        passwordController: _loginPassword,
                                        isLoading: isLoading,
                                        message: message,
                                        onSubmit: () async {
                                          await ref
                                              .read(authControllerProvider.notifier)
                                              .login(_loginEmail.text.trim(), _loginPassword.text);
                                        },
                                      ),
                                      _AuthForm(
                                        title: 'Sign up',
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
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: isLoading
                        ? null
                        : () {
                            ref.read(authControllerProvider.notifier).continueAsGuest();
                          },
                    icon: const Icon(Icons.person_outline),
                    label: const Text('Continue as Guest'),
                  ),
                  const Spacer(),
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
      ),
    );
  }
}

class _AuthForm extends StatelessWidget {
  final String title;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final bool isLoading;
  final String? message;
  final Future<void> Function() onSubmit;

  const _AuthForm({
    required this.title,
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
        children: [
          if (message != null) ...[
            Text(message!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 12),
          ],
          TextField(
            controller: emailController,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(labelText: 'Email'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: passwordController,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Password'),
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
        ],
      ),
    );
  }
}
