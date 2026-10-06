import http from 'k6/http';
import { check } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const measureDuration = new Trend('measure_duration', true);
const measureReqs = new Counter('measure_reqs');
const WARMUP_MS = 10000;
const BASE = 'https://csce-500-project.onrender.com';

export const options = {
  scenarios: {
    write_path: {
      executor: 'constant-vus',
      vus: 16,
      duration: '70s',
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const login = http.post(`${BASE}/api/auth/login`,
    JSON.stringify({ email: 'alex@example.com', password: 'ClassDemo123!' }),
    { headers: { 'Content-Type': 'application/json' } });
  const token = login.json('access_token');
  return { token: token, itemId: 3 };
}

const startTime = Date.now();

export default function (data) {
  const res = http.put(`${BASE}/api/cart/${data.itemId}`,
    JSON.stringify({ quantity: 1 }),
    { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${data.token}` } });
  check(res, { 'status is 200': (r) => r.status === 200 });

  if (Date.now() - startTime > WARMUP_MS) {
    measureDuration.add(res.timings.duration);
    measureReqs.add(1);
  }
}