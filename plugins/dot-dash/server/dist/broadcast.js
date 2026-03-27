const WS_OPEN = 1;
export class Broadcaster {
  clients = new Set();
  add(ws) {
    this.clients.add(ws);
  }
  remove(ws) {
    this.clients.delete(ws);
  }
  send(msg) {
    const data = JSON.stringify(msg);
    const dead = [];
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
  size() {
    return this.clients.size;
  }
}
