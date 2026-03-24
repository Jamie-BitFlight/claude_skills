import type { WsMessage } from './types.js';

interface WsClient {
  send(data: string): void;
  readyState: number;
}

const WS_OPEN = 1;

export class Broadcaster {
  private clients = new Set<WsClient>();

  add(ws: WsClient): void {
    this.clients.add(ws);
  }

  remove(ws: WsClient): void {
    this.clients.delete(ws);
  }

  send(msg: WsMessage): void {
    const data = JSON.stringify(msg);
    const dead: WsClient[] = [];
    for (const client of this.clients) {
      if (client.readyState !== WS_OPEN) {
        dead.push(client);
        continue;
      }
      try {
        client.send(data);
      } catch {
        dead.push(client);
      }
    }
    for (const d of dead) this.clients.delete(d);
  }

  size(): number {
    return this.clients.size;
  }
}
