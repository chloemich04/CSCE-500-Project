import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const BASE = 'http://127.0.0.1:8000';

// Une métrique de latence par endpoint testé
const t_product_single = new Trend('t_product_single', true);  // 1 table, 1 résultat
const t_product_list   = new Trend('t_product_list', true);    // 1 table, liste
const t_cat_small      = new Trend('t_cat_small', true);        // join, petite catégorie (Sports)
const t_cat_big        = new Trend('t_cat_big', true);          // join, grosse catégorie (Games)
const t_orders         = new Trend('t_orders', true);           // 3 tables join

export const options = {
  scenarios: {
    m4: { executor: 'constant-vus', vus: 8, duration: '60s' },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const login = http.post(`${BASE}/api/auth/login`,
    JSON.stringify({ email: 'user4325@example.com', password: 'ClassDemo123!' }),
    { headers: { 'Content-Type': 'application/json' } });
  return { token: login.json('access_token') };
}

export default function (data) {
  const h = { headers: { 'Authorization': `Bearer ${data.token}` } };

  // 1. GET /api/products/{id} — 1 table, 1 résultat
  let r = http.get(`${BASE}/api/products/1`, h);
  check(r, { 'single 200': (x) => x.status === 200 });
  t_product_single.add(r.timings.duration);

  // 2. GET /api/products — 1 table, liste
  r = http.get(`${BASE}/api/products`, h);
  check(r, { 'list 200': (x) => x.status === 200 });
  t_product_list.add(r.timings.duration);

  // 3. GET /api/categories/5/products — join, PETITE catégorie (Sports, 664)
  r = http.get(`${BASE}/api/categories/5/products`, h);
  check(r, { 'cat small 200': (x) => x.status === 200 });
  t_cat_small.add(r.timings.duration);

  // 4. GET /api/categories/8/products — join, GROSSE catégorie (Games, 3194)
  r = http.get(`${BASE}/api/categories/8/products`, h);
  check(r, { 'cat big 200': (x) => x.status === 200 });
  t_cat_big.add(r.timings.duration);

  // 5. GET /api/orders — 3 tables join (user4325 a beaucoup de commandes)
  r = http.get(`${BASE}/api/orders`, h);
  check(r, { 'orders 200': (x) => x.status === 200 });
  t_orders.add(r.timings.duration);
}