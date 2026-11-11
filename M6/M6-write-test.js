// M6 write-heavy load test: every iteration = 4 writes on the customer's data
// (add to cart x2, update quantity, checkout). Each VU is its own customer, so the
// writes of different VUs never touch the same cart; checkout decrements the stock of
// a small set of "hot" products (best-sellers), like a real sale.
//
//   k6 run -e LABEL=before_16 -e VUS=16 M6/M6-write-test.js
import http from 'k6/http';
import { check } from 'k6';
import { Trend, Counter } from 'k6/metrics';
import encoding from 'k6/encoding';

const BASE = __ENV.BASE || 'http://127.0.0.1:8000';
const VUS = Number(__ENV.VUS || 8);
const DURATION = __ENV.DURATION || '60s';
const WARMUP_MS = 10000;
const HOT_PRODUCTS = 20;

const writeDuration = new Trend('write_duration', true);
const checkoutDuration = new Trend('checkout_duration', true);
const writes = new Counter('writes_measured');
const failures = new Counter('write_failures');

export const options = {
  setupTimeout: '180s',
  scenarios: { writes: { executor: 'constant-vus', vus: VUS, duration: DURATION } },
  // per-shard sub-metrics (shard read from the JWT): lets us compare shard_0 users before/after
  thresholds: {
    'write_duration{shard:0}': ['max>=0'], 'write_duration{shard:1}': ['max>=0'],
    'writes_measured{shard:0}': ['count>=0'], 'writes_measured{shard:1}': ['count>=0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const JSON_H = { 'Content-Type': 'application/json' };

export function setup() {
  const tokens = [];
  for (let i = 1; i <= VUS; i++) {
    // user1000+ : customers from the M4 seed, one per VU
    const r = http.post(`${BASE}/api/auth/login`,
      JSON.stringify({ email: `user${1000 + i}@example.com`, password: 'ClassDemo123!' }),
      { headers: JSON_H });
    if (r.status !== 200) throw new Error(`login user${1000 + i}: ${r.status} ${r.body}`);
    tokens.push(r.json('access_token'));
  }
  const shards = tokens.map((t) => JSON.parse(encoding.b64decode(t.split('.')[1], 'rawurl', 's')).shard);
  const p = http.get(`${BASE}/api/products?page=1&page_size=${HOT_PRODUCTS}`,
    { headers: { Authorization: `Bearer ${tokens[0]}` } });
  const products = p.json().map((x) => x.id);
  // empty any cart left by a previous run
  for (const t of tokens) http.post(`${BASE}/api/orders`, null, { headers: { Authorization: `Bearer ${t}` } });
  return { tokens, products, shards };
}

const start = Date.now();

let SHARD = '0';

function record(res, name, ok) {
  const passed = check(res, { [`${name} ok`]: () => ok });
  if (Date.now() - start > WARMUP_MS) {
    writeDuration.add(res.timings.duration, { name, shard: SHARD });
    writes.add(1, { name, shard: SHARD });
    if (!passed) failures.add(1, { name });
  }
  return res;
}

export default function (data) {
  const token = data.tokens[(__VU - 1) % data.tokens.length];
  SHARD = String(data.shards[(__VU - 1) % data.shards.length]);
  const h = { headers: { ...JSON_H, Authorization: `Bearer ${token}` } };
  const pick = () => data.products[Math.floor(Math.random() * data.products.length)];

  const p1 = pick();
  let p2 = pick();
  while (p2 === p1 && data.products.length > 1) p2 = pick();

  let r = http.post(`${BASE}/api/cart`, JSON.stringify({ product_id: p1, quantity: 1 }), { ...h, tags: { name: 'add_to_cart' } });
  record(r, 'add_to_cart', r.status === 201);
  r = http.post(`${BASE}/api/cart`, JSON.stringify({ product_id: p2, quantity: 1 }), { ...h, tags: { name: 'add_to_cart' } });
  record(r, 'add_to_cart', r.status === 201);

  const items = r.status === 201 ? r.json('items') : [];
  if (items && items.length) {
    r = http.put(`${BASE}/api/cart/${items[0].id}`, JSON.stringify({ quantity: 2 }), { ...h, tags: { name: 'update_qty' } });
    record(r, 'update_qty', r.status === 200);
  }

  r = http.post(`${BASE}/api/orders`, null, { ...h, tags: { name: 'checkout' } });
  record(r, 'checkout', r.status === 201);
  if (Date.now() - start > WARMUP_MS) checkoutDuration.add(r.timings.duration);
}

export function handleSummary(data) {
  const m = data.metrics;
  const secs = (Number((DURATION.match(/\d+/) || [60])[0]) * 1000 - WARMUP_MS) / 1000;
  const row = {
    label: __ENV.LABEL || 'run',
    vus: VUS,
    writes: m.writes_measured ? m.writes_measured.values.count : 0,
    writes_per_s: m.writes_measured ? +(m.writes_measured.values.count / secs).toFixed(1) : 0,
    failures: m.write_failures ? m.write_failures.values.count : 0,
    p50: m.write_duration ? +m.write_duration.values.med.toFixed(0) : null,
    p95: m.write_duration ? +m.write_duration.values['p(95)'].toFixed(0) : null,
    p99: m.write_duration ? +m.write_duration.values['p(99)'].toFixed(0) : null,
    checkout_p50: m.checkout_duration ? +m.checkout_duration.values.med.toFixed(0) : null,
    checkout_p95: m.checkout_duration ? +m.checkout_duration.values['p(95)'].toFixed(0) : null,
  };
  for (const sh of ['0', '1']) {
    const d = m[`write_duration{shard:${sh}}`];
    const c = m[`writes_measured{shard:${sh}}`];
    row[`shard${sh}_writes`] = c ? c.values.count : 0;
    row[`shard${sh}_p50`] = d && d.values.med !== undefined ? +d.values.med.toFixed(0) : null;
    row[`shard${sh}_p95`] = d && d.values['p(95)'] !== undefined ? +d.values['p(95)'].toFixed(0) : null;
  }
  return {
    stdout: JSON.stringify(row) + '\n',
    [`M6/results/${row.label}.json`]: JSON.stringify({ row, metrics: m }, null, 1),
  };
}
