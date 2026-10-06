import http from 'k6/http';
import { check } from 'k6';
import { Trend, Counter } from 'k6/metrics';

// Métriques "measure only" : on ne compte QUE la phase de mesure (après warmup)
const measureDuration = new Trend('measure_duration', true);
const measureReqs = new Counter('measure_reqs');

const WARMUP_MS = 10000; // 10s de warmup à jeter

export const options = {
  scenarios: {
    read_path: {
      executor: 'constant-vus',
      vus: 16,           // ← CHANGE ce nombre à chaque palier : 1, 4, 8, 16
      duration: '70s',   // 10s warmup + 60s mesure
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const startTime = Date.now();

export default function () {
  const res = http.get('https://csce-500-project.onrender.com/api/products');
  check(res, { 'status is 200': (r) => r.status === 200 });

  // On n'enregistre dans nos métriques QUE si le warmup est passé
  if (Date.now() - startTime > WARMUP_MS) {
    measureDuration.add(res.timings.duration);
    measureReqs.add(1);
  }
}