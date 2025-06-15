import 'dart:math' as math;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

class SignupPage extends StatefulWidget {
  const SignupPage({super.key});

  @override
  _SignupPageState createState() => _SignupPageState();
}

class _SignupPageState extends State<SignupPage>
    with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();
  final FirebaseAuth _auth = FirebaseAuth.instance;

  late final AnimationController _controller;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(seconds: 20),
      vsync: this,
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  String cleanEmail(String email) {
    return email.replaceAll(RegExp(r'[^\x00-\x7F]'), '').trim();
  }

  void _signup() async {
    if (_formKey.currentState?.validate() ?? false) {
      setState(() {
        _isLoading = true;
      });

      try {
        print('Starting signup process...'); // Debug print

        final UserCredential userCredential =
            await _auth.createUserWithEmailAndPassword(
          email: cleanEmail(_emailController.text),
          password: _passwordController.text,
        );
        await userCredential.user
            ?.updateDisplayName(_usernameController.text.trim());

// (אופציונלי) רענון המשתמש לקבלת העדכון
        await userCredential.user?.reload();

        print('User created: ${userCredential.user?.uid}'); // Debug print

        // Stop loading and show success immediately after user creation
        setState(() {
          _isLoading = false;
        });

        // Show success dialog first
        _showSuccessDialog();

        // Try to save to Firestore in background (optional)
        FirebaseFirestore.instance
            .collection('users')
            .doc(userCredential.user?.uid)
            .set({
          'username': _usernameController.text.trim(),
          'email': cleanEmail(_emailController.text),
          'createdAt': FieldValue.serverTimestamp(),
        }).then((_) {
          print('User data saved to Firestore'); // Debug print
        }).catchError((error) {
          print('Firestore save failed: $error');
          // Handle Firestore error if needed
        });
      } on FirebaseAuthException catch (e) {
        setState(() {
          _isLoading = false;
        });

        String message;
        switch (e.code) {
          case 'weak-password':
            message = 'The password is too weak';
            break;
          case 'email-already-in-use':
            message = 'The email is already in use';
            break;
          case 'invalid-email':
            message = 'The email address is not valid';
            break;
          default:
            message = 'Registration failed: ${e.message}';
        }

        _showErrorSnackBar(message);
      } catch (e) {
        setState(() {
          _isLoading = false;
        });

        print('Unexpected error: $e'); // Debug print
        _showErrorSnackBar('An unexpected error occurred. Please try again.');
      }
    }
  }

  void _showErrorSnackBar(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  void _showSuccessDialog() {
    if (mounted) {
      showDialog(
        context: context,
        barrierDismissible: false, // Prevent dismissing by tapping outside
        builder: (BuildContext context) {
          return AlertDialog(
            title: const Row(
              children: [
                Icon(Icons.check_circle, color: Colors.green, size: 28),
                SizedBox(width: 8),
                Text('Registration Successful'),
              ],
            ),
            content: const Text(
              'You have been successfully registered! Welcome to our community.',
              style: TextStyle(fontSize: 16),
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop(); // Close dialog
                  // Navigate to home or login page
                  Navigator.pushReplacementNamed(context, '/home');
                },
                style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFFc6a2df),
                ),
                child: const Text(
                  'Continue',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
          );
        },
      );
    }
  }

  Widget _buildBackgroundGrid() {
    return LayoutBuilder(
      builder: (context, constraints) {
        const double logoSize = 30.0;
        const double spacing = 8.0;
        int columns = 25;
        int rows = (constraints.maxHeight / (logoSize + spacing)).ceil() + 2;

        return GridView.builder(
          physics: const NeverScrollableScrollPhysics(),
          itemCount: columns * rows,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            mainAxisSpacing: spacing,
            crossAxisSpacing: spacing,
            childAspectRatio: 1,
          ),
          itemBuilder: (context, index) {
            return AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                return Transform.rotate(
                  angle: _controller.value * 2 * math.pi,
                  child: child,
                );
              },
              child: SizedBox(
                width: logoSize,
                height: logoSize,
                child: Image.asset(
                  'assets/logo1.png',
                  fit: BoxFit.contain,
                ),
              ),
            );
          },
        );
      },
    );
  }

  final Color _focusedBorderColor = const Color(0xFFc6a2df);

  InputDecoration _inputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      border: const OutlineInputBorder(),
      alignLabelWithHint: true,
      contentPadding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      focusedBorder: OutlineInputBorder(
        borderSide: BorderSide(
          color: _focusedBorderColor,
          width: 2.0,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    const backgroundColor = Color(0xFFfdf8f4);

    return Scaffold(
      backgroundColor: backgroundColor,
      body: Stack(
        children: [
          Positioned.fill(
            child: IgnorePointer(
              child: Opacity(
                opacity: 0.25,
                child: _buildBackgroundGrid(),
              ),
            ),
          ),
          SafeArea(
            child: SingleChildScrollView(
              child: Container(
                width: double.infinity,
                constraints: BoxConstraints(
                  minHeight: MediaQuery.of(context).size.height -
                      MediaQuery.of(context).padding.top -
                      MediaQuery.of(context).padding.bottom,
                ),
                child: Center(
                  child: Container(
                    margin: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 20),
                    padding: const EdgeInsets.all(20),
                    constraints: const BoxConstraints(
                      maxWidth: 500,
                    ),
                    decoration: BoxDecoration(
                      color: backgroundColor,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.1),
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: <Widget>[
                          const SizedBox(height: 20),
                          SizedBox(
                            width: 140,
                            height: 140,
                            child: Image.asset(
                              'assets/poster.png',
                              fit: BoxFit.contain,
                            ),
                          ),
                          const SizedBox(height: 10),
                          const Text(
                            'Join Us!',
                            style: TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.bold,
                              fontFamily: 'Poppins',
                            ),
                          ),
                          const SizedBox(height: 24),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 340),
                            child: TextFormField(
                              controller: _usernameController,
                              decoration: _inputDecoration('Username'),
                              enabled: !_isLoading, // Disable during loading
                              validator: (value) =>
                                  value == null || value.isEmpty
                                      ? 'Please enter your username'
                                      : null,
                            ),
                          ),
                          const SizedBox(height: 16),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 340),
                            child: TextFormField(
                              controller: _emailController,
                              decoration: _inputDecoration('Email'),
                              keyboardType: TextInputType.emailAddress,
                              enabled: !_isLoading, // Disable during loading
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please enter your email';
                                }
                                if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$')
                                    .hasMatch(value)) {
                                  return 'Please enter a valid email';
                                }
                                return null;
                              },
                            ),
                          ),
                          const SizedBox(height: 16),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 340),
                            child: TextFormField(
                              controller: _passwordController,
                              obscureText: true,
                              decoration: _inputDecoration('Password'),
                              enabled: !_isLoading, // Disable during loading
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please enter your password';
                                }
                                if (value.length < 6) {
                                  return 'Password must be at least 6 characters';
                                }
                                return null;
                              },
                            ),
                          ),
                          const SizedBox(height: 16),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 340),
                            child: TextFormField(
                              controller: _confirmPasswordController,
                              obscureText: true,
                              decoration: _inputDecoration('Confirm Password'),
                              enabled: !_isLoading, // Disable during loading
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please confirm your password';
                                }
                                if (value != _passwordController.text) {
                                  return 'Passwords do not match';
                                }
                                return null;
                              },
                            ),
                          ),
                          const SizedBox(height: 24),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 340),
                            child: SizedBox(
                              width: double.infinity,
                              child: ElevatedButton(
                                onPressed: _isLoading ? null : _signup,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: _focusedBorderColor,
                                  foregroundColor: Colors.black,
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 16),
                                  textStyle: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                  elevation: 4,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                ),
                                child: _isLoading
                                    ? const Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        children: [
                                          SizedBox(
                                            height: 20,
                                            width: 20,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              valueColor:
                                                  AlwaysStoppedAnimation<Color>(
                                                      Colors.black),
                                            ),
                                          ),
                                          SizedBox(width: 12),
                                          Text('Signing Up...'),
                                        ],
                                      )
                                    : const Text('Sign Up'),
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
