// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The health listener (D-ID-OI-05; P-07): plain HTTP, bound to 127.0.0.1
// inside the container, on no network. `GET /` answers 204 and nothing else;
// it serves no data. The Compose healthcheck calls it (healthcheck.ts).
import { createServer, type Server } from 'node:http';

export const HEALTH_HOST = '127.0.0.1';

export function createHealthServer(): Server {
  return createServer((request, response) => {
    request.resume();
    response.statusCode = request.method === 'GET' && request.url === '/' ? 204 : 404;
    response.end();
  });
}

export function listenHealth(port: number): Promise<Server> {
  const server = createHealthServer();
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, HEALTH_HOST, () => resolve(server));
  });
}
