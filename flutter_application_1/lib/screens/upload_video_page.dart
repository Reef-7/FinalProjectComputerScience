import 'package:flutter/material.dart';
import 'dart:html' as html;
import 'dart:async';
import 'package:http/http.dart' as http;
import 'predictions_page.dart';

class UploadVideoPage extends StatefulWidget {
  const UploadVideoPage({super.key});

  @override
  _UploadVideoPageState createState() => _UploadVideoPageState();
}

class _UploadVideoPageState extends State<UploadVideoPage>
    with SingleTickerProviderStateMixin {
  String? _videoFileName;
  bool _isLoading = false;

  late AnimationController _controller;
  late Animation<Offset> _offsetAnimation;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    _offsetAnimation = TweenSequence<Offset>([
      TweenSequenceItem(
          tween: Tween(begin: Offset.zero, end: Offset(0.03, 0)), weight: 50),
      TweenSequenceItem(
          tween: Tween(begin: Offset(0.03, 0), end: Offset(-0.03, 0)),
          weight: 50),
    ]).animate(CurvedAnimation(parent: _controller, curve: Curves.linear));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _pickVideo() async {
    html.FileUploadInputElement uploadInput = html.FileUploadInputElement();
    uploadInput.accept = 'video/mp4,video/webm,video/ogg';
    uploadInput.click();

    uploadInput.onChange.listen((e) async {
      final files = uploadInput.files;
      if (files!.isEmpty) return;

      setState(() {
        _videoFileName = files[0].name;
      });

      await sendVideoToMultipleServers(files[0]);
    });
  }

  Future<void> sendVideoToMultipleServers(html.File file) async {
    setState(() {
      _isLoading = true;
    });

    final reader = html.FileReader();
    final completer = Completer<List<int>>();
    reader.readAsArrayBuffer(file);

    reader.onLoadEnd.listen((e) {
      completer.complete(reader.result as List<int>);
    });

    reader.onError.listen((e) {
      completer.completeError(Exception("Failed to read file"));
    });

    try {
      final bytes = await completer.future;

      final uris = [
        Uri.parse('http://localhost:5000/upload/movenet'),
        Uri.parse('http://localhost:5000/upload/yolo'),
        Uri.parse('http://localhost:5000/upload/mediapipe'),
      ];

      for (final uri in uris) {
        final request = http.MultipartRequest('POST', uri);
        request.files.add(http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: file.name,
        ));

        try {
          final response = await request.send();
          if (response.statusCode == 200) {
            print('Uploaded to $uri successfully');
          } else {
            print('Upload to $uri failed: ${response.statusCode}');
          }
        } catch (e) {
          print('Error uploading to $uri: $e');
        }
      }

      if (mounted) {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (context) => const PredictionPage()),
        );
      }
    } catch (e) {
      print("Error reading file: $e");
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Widget _buildInfoBox({
    required String title,
    required String description,
    required IconData icon,
    required Color color,
  }) {
    return Expanded(
      child: GestureDetector(
        onTap: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$title tapped!')),
          );
        },
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 8.0),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(20),
            boxShadow: const [
              BoxShadow(
                color: Colors.black12,
                blurRadius: 6,
                offset: Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 44, color: Colors.black87),
              const SizedBox(height: 16),
              Text(
                title,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'Raleway',
                ),
              ),
              const SizedBox(height: 12),
              Text(
                description,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  color: Colors.black87,
                  fontFamily: 'Raleway',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final username =
        ModalRoute.of(context)?.settings.arguments as String? ?? 'User';

    return Scaffold(
      backgroundColor: const Color(0xFFfdf8f4),
      appBar: AppBar(
        backgroundColor: const Color(0xFFfdf8f4),
        toolbarHeight: 80,
        elevation: 0,
        title: Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Image.asset(
              'assets/poster.png',
              height: 80,
              fit: BoxFit.contain,
            ),
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            const SizedBox(height: 2),
            RotationTransition(
              turns: _controller,
              child: SlideTransition(
                position: _offsetAnimation,
                child: Image.asset(
                  'assets/logo1.png',
                  height: 120,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              "Welcome, $username!",
              style: TextStyle(
                fontSize: 40,
                fontWeight: FontWeight.bold,
                fontFamily: 'Raleway',
                color: Colors.black,
              ),
            ),
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.only(top: 20.0),
              child: Container(
                width: double.infinity,
                color: const Color(0xFFd5c4e1),
                padding: const EdgeInsets.symmetric(
                    horizontal: 32.0, vertical: 35.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text(
                          "Upload a video of your baby to begin...",
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'Raleway',
                            color: Colors.black,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Image.asset(
                          'assets/baby.png',
                          height: 40,
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Text(
                      _videoFileName != null
                          ? "Selected video: $_videoFileName"
                          : "No video selected",
                      style: const TextStyle(fontSize: 16, color: Colors.black),
                    ),
                    const SizedBox(height: 20),

                    // כפתור לבחור וידאו
                    Center(
                      child: SizedBox(
                        width: 280,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.video_library,
                              color: Colors.black),
                          label: const Padding(
                            padding: EdgeInsets.symmetric(
                                vertical: 14.0, horizontal: 8),
                            child: Text(
                              "Pick a Video",
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                                fontFamily: 'Raleway',
                                color: Colors.black,
                              ),
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFFfdf8f4),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                            elevation: 6,
                            shadowColor: const Color(0xFFfdf8f4),
                          ),
                          onPressed: _isLoading ? null : _pickVideo,
                        ),
                      ),
                    ),

                    // אינדיקטור טעינה בזמן העיבוד
                    if (_isLoading)
                      Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: const [
                            CircularProgressIndicator(),
                            SizedBox(width: 16),
                            Text("Processing video, please wait..."),
                          ],
                        ),
                      ),

                    const SizedBox(height: 20),

                    // כפתור צפייה בתוצאות
                    Center(
                      child: SizedBox(
                        width: 280,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.analytics,
                              size: 28, color: Colors.black),
                          label: const Padding(
                            padding: EdgeInsets.symmetric(
                                vertical: 14.0, horizontal: 8),
                            child: Text(
                              "View Results",
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                                fontFamily: 'Raleway',
                                color: Colors.black,
                              ),
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFFfdf8f4),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                            elevation: 6,
                            shadowColor: const Color(0xFFfdf8f4),
                          ),
                          onPressed: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (context) => const PredictionPage(),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildInfoBox(
                    title: "Video Analysis",
                    description:
                        "Uses video analysis to track\ninfant movements",
                    icon: Icons.videocam,
                    color: Colors.green[100]!,
                  ),
                  _buildInfoBox(
                    title: "Mobility Rating",
                    description:
                        "Providing a mobility rating\nand overall movement assessment",
                    icon: Icons.bar_chart,
                    color: Colors.grey[400]!,
                  ),
                  _buildInfoBox(
                    title: "Early Intervention",
                    description: "Allows for\ntimely intervention",
                    icon: Icons.schedule,
                    color: Colors.green[100]!,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
