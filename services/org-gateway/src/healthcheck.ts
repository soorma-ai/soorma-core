// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Compose healthcheck (D-ID-OI-05): GET the health listener on loopback;
// exit 0 on 204, 1 on anything else or within 2 seconds of no answer. The
// distroless image has no shell or curl, so it is a Node script.
import { request } from 'node:http';

const port = Number(process.env.SOORMA_HEALTH_PORT ?? 8080);
const req = request({ host: '127.0.0.1', port, path: '/', method: 'GET', timeout: 2000 }, (res) => {
  res.resume();
  process.exit(res.statusCode === 204 ? 0 : 1);
});
req.on('timeout', () => req.destroy());
req.on('error', () => process.exit(1));
req.end();
