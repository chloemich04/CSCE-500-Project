import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const BASE = __ENV.BASE || 'http://127.0.0.1:8000';

const t_none     = new Trend('t_search_none', true);      // 0 results
const t_one      = new Trend('t_search_one', true);       // 1
const t_small    = new Trend('t_search_small', true);     // 42
const t_medium   = new Trend('t_search_medium', true);    // 118
const t_large    = new Trend('t_search_large', true);     // 3225
const t_filtered = new Trend('t_search_filtered', true);
const t_deep     = new Trend('t_search_deep_page', true);
const t_baseline = new Trend('t_products_page', true);
// old ILIKE search
const t_old_one   = new Trend('t_ilike_one', true);
const t_old_large = new Trend('t_ilike_large', true);

export const options = {
  scenarios: {
    m5: { executor: 'constant-vus', vus: 8, duration: '60s' },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const login = http.post(`${BASE}/api/auth/login`,
    JSON.stringify({ email: 'user4325@example.com', password: 'ClassDemo123!' }),
    { headers: { 'Content-Type': 'application/json' } });
  return { token: login.json('access_token') };
}

function hit(url, trend, name, expectResults) {
  const r = http.get(url);
  check(r, {
    [`${name} 200`]: (x) => x.status === 200,
    [`${name} results`]: (x) => x.status === 200 && (x.json('total') > 0) === expectResults,
  });
  trend.add(r.timings.duration);
}

export default function (data) {
  const h = { headers: { 'Authorization': `Bearer ${data.token}` } };

  hit(`${BASE}/api/search?q=zzzqx`, t_none, 'none', false);
  hit(`${BASE}/api/search?q=${encodeURIComponent('azure table')}`, t_one, 'one', true);
  hit(`${BASE}/api/search?q=azure`, t_small, 'small', true);
  hit(`${BASE}/api/search?q=blue`, t_medium, 'medium', true);
  hit(`${BASE}/api/search?q=game`, t_large, 'large', true);
  hit(`${BASE}/api/search?q=game&category=Games&max_price=20`, t_filtered, 'filtered', true);
  hit(`${BASE}/api/search?q=game&page=30`, t_deep, 'deep', true);

  let r = http.get(`${BASE}/api/products?page=1&page_size=20`, h);
  check(r, { 'products 200': (x) => x.status === 200 });
  t_baseline.add(r.timings.duration);

  r = http.get(`${BASE}/api/products/search?q=${encodeURIComponent('azure table')}&page=1&page_size=20`, h);
  check(r, { 'ilike one 200': (x) => x.status === 200 });
  t_old_one.add(r.timings.duration);

  r = http.get(`${BASE}/api/products/search?q=game&page=1&page_size=20`, h);
  check(r, { 'ilike large 200': (x) => x.status === 200 });
  t_old_large.add(r.timings.duration);
}
