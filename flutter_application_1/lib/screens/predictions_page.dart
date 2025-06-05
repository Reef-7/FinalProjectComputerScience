import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';

class PredictionPage extends StatefulWidget {
  const PredictionPage({super.key});

  @override
  State<PredictionPage> createState() => _PredictionPageState();
}

class _PredictionPageState extends State<PredictionPage> {
  List<FlSpot> movementSpots = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchPredictionData();
  }

  Future<void> fetchPredictionData() async {
    try {
      final response =
          await http.get(Uri.parse('http://localhost:8080/predict'));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);

        // צור נקודות לגרף מהנתונים
        final spots = data.map<FlSpot>((item) {
          final double x = (item['window_id'] as num).toDouble();
          final double y = (item['movement_prediction'] as num).toDouble();
          return FlSpot(x, y);
        }).toList();

        setState(() {
          movementSpots = spots;
          isLoading = false;
        });
      } else {
        throw Exception('Failed to load prediction data');
      }
    } catch (e) {
      print('Error fetching predictions: $e');
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('חיזויים'),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16.0),
              child: LineChart(
                LineChartData(
                  lineBarsData: [
                    LineChartBarData(
                      spots: movementSpots,
                      isCurved: true,
                      barWidth: 2,
                      color: Colors.blue,
                      dotData: FlDotData(show: false),
                    )
                  ],
                  titlesData: FlTitlesData(
                    leftTitles:
                        AxisTitles(sideTitles: SideTitles(showTitles: true)),
                    bottomTitles: AxisTitles(
                      sideTitles:
                          SideTitles(showTitles: true, reservedSize: 22),
                    ),
                  ),
                  borderData: FlBorderData(show: true),
                  gridData: FlGridData(show: true),
                ),
              ),
            ),
    );
  }
}
