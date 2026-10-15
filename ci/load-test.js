import http from 'k6/http';
import { check, sleep } from 'k6';

const target = __ENV.LOAD_TEST_URL;
if (!target || !/^https?:\/\//.test(target)) {
  throw new Error('LOAD_TEST_URL must be an operator-approved isolated test endpoint');
}
export const options = {
  vus: 2,
  duration: '30s',
  thresholds: { http_req_failed: ['rate<0.01'] },
};
export default function () {
  const response = http.get(target);
  check(response, { 'HTTP success': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);
}
