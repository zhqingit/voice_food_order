import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Signed in.'),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () async {
                await ref.read(authControllerProvider.notifier).logoutCurrent();
              },
              child: const Text('Logout this device'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: () async {
                await ref.read(authControllerProvider.notifier).logoutAll();
              },
              child: const Text('Logout all sessions'),
            ),
          ],
        ),
      ),
    );
  }
}
