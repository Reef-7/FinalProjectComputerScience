import 'package:flutter/material.dart';
import 'dart:html' as html;
import 'dart:async';
import 'package:http/http.dart' as http;

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
    reader.readAsArrayBuffer(file);
    reader.onLoadEnd.listen((e) async {
      final bytes = reader.result as List<int>;

      // רשימת כתובות השרתים
      final uris = [
        Uri.parse('http://127.0.0.1:5000/upload'),
        Uri.parse('http://127.0.0.1:5004/upload'),
        Uri.parse('http://127.0.0.1:5002/upload')
      ];

      for (final uri in uris) {
        final request = http.MultipartRequest('POST', uri);
        request.files.add(
          http.MultipartFile.fromBytes('file', bytes, filename: file.name),
        );

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
    });
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
          ],
        ),
      ),
    );
  }
}
