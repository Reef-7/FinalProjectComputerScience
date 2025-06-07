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
  int selectedGraph = 0;

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

  Widget buildGraphView() {
    switch (selectedGraph) {
      case 0:
        return LineChart(
          LineChartData(
            minY: 0,
            maxY: 10,
            lineBarsData: [
              LineChartBarData(
                spots: movementSpots,
                isCurved: true,
                barWidth: 2,
                color: Colors.blue,
                dotData: FlDotData(
                  show: true,
                  getDotPainter: (spot, percent, barData, index) {
                    if (spot.x % 1 == 0) {
                      return FlDotCirclePainter(
                        radius: 4,
                        color: Colors.red,
                        strokeWidth: 2,
                        strokeColor: Colors.black,
                      );
                    }
                    return FlDotCirclePainter(
                      radius: 0,
                      color: Colors.transparent,
                      strokeWidth: 0,
                      strokeColor: Colors.transparent,
                    );
                  },
                ),
              )
            ],
            titlesData: FlTitlesData(
              leftTitles: AxisTitles(
                axisNameWidget: const Text('Movement Score'),
                axisNameSize: 32,
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 40,
                  getTitlesWidget: (value, meta) {
                    return Text(
                      value.toStringAsFixed(1),
                      style: const TextStyle(fontSize: 12),
                      textAlign: TextAlign.center,
                    );
                  },
                ),
              ),
              bottomTitles: AxisTitles(
                axisNameWidget: const Text('Time Window'),
                axisNameSize: 28,
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 22,
                  getTitlesWidget: (value, meta) {
                    return Text(
                      value.toInt().toString(),
                      style: const TextStyle(fontSize: 12),
                    );
                  },
                ),
              ),
            ),
            borderData: FlBorderData(show: true),
            gridData: FlGridData(show: true),
          ),
        );

      case 1:
        return Center(
            child: Text('Dominant Knee', style: TextStyle(fontSize: 20)));
      case 2:
        return Center(
            child: Text('Dominant Elbow', style: TextStyle(fontSize: 20)));
      default:
        return Container();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Results'),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Image.asset(
                            'assets/Movement.jpg',
                            width: 64,
                            height: 64,
                            filterQuality: FilterQuality.high,
                          ),
                          const SizedBox(height: 8),
                          ElevatedButton(
                            onPressed: () => setState(() => selectedGraph = 0),
                            child: const Text('Movement Score'),
                          ),
                        ],
                      ),
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Image.asset(
                            'assets/knee.jpg',
                            width: 64,
                            height: 64,
                            filterQuality: FilterQuality.high,
                          ),
                          const SizedBox(height: 8),
                          ElevatedButton(
                            onPressed: () => setState(() => selectedGraph = 1),
                            child: const Text('Dominant Knee'),
                          ),
                        ],
                      ),
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Image.asset(
                            'assets/elbow.jpg',
                            width: 64,
                            height: 64,
                            filterQuality: FilterQuality.high,
                          ),
                          const SizedBox(height: 8),
                          ElevatedButton(
                            onPressed: () => setState(() => selectedGraph = 2),
                            child: const Text('Dominant Elbow'),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Expanded(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 400),
                      transitionBuilder: (child, animation) {
                        return FadeTransition(opacity: animation, child: child);
                      },
                      child: SizedBox(
                        key: ValueKey(selectedGraph),
                        width: double.infinity,
                        child: buildGraphView(),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
