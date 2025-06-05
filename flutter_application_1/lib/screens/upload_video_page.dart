import 'package:flutter/material.dart';
import 'dart:html' as html;
import 'dart:async';
import 'package:http/http.dart' as http;
import 'dart:html' as html;
import 'predictions_page.dart';

class UploadVideoPage extends StatefulWidget {
  const UploadVideoPage({super.key});

  @override
  _UploadVideoPageState createState() => _UploadVideoPageState();
}

class _UploadVideoPageState extends State<UploadVideoPage> {
  String? _videoFileName;

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

      // שליחה לשרת
      await sendVideoToMultipleServers(files[0]);
    });
  }

  Future<void> sendVideoToMultipleServers(html.File file) async {
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
        Uri.parse('http://localhost:5000/upload/mediapipe')
      ];

      for (final uri in uris) {
        final request = http.MultipartRequest('POST', uri);
        request.files.add(
            http.MultipartFile.fromBytes('file', bytes, filename: file.name));

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
    } catch (e) {
      print("Error reading file: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Upload Video")),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              "Select a video to upload",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 20),
            Text(
              _videoFileName != null
                  ? "Selected video: $_videoFileName"
                  : "No video selected",
              style: TextStyle(fontSize: 16),
            ),
            SizedBox(height: 20),
            ElevatedButton.icon(
              icon: Icon(Icons.video_library),
              label: Text("Pick Video"),
              onPressed: _pickVideo,
            ),
            SizedBox(height: 40),
            //results page navigation
            MouseRegion(
              cursor: SystemMouseCursors.click,
              child: ElevatedButton.icon(
                icon: Icon(Icons.analytics, size: 28),
                label: Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 14.0, horizontal: 8),
                  child: Text(
                    "Results",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepPurple,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 6,
                  shadowColor: Colors.deepPurpleAccent,
                ),
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                        builder: (context) => const PredictionPage()),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
