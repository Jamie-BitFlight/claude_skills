import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from '@hono/node-server';
import { serveStatic } from '@hono/node-server/serve-static';
import { createNodeWebSocket } from '@hono/node-server/ws';
import { Hono } from 'hono';
import { loadOrCreateToken, validateToken } from './auth.js';
import { Broadcaster } from './broadcast.js';
import { SessionManager } from './sessions.js';
import type { WsMessage } from './types.js';
import { createWatcher } from './watcher.js';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const PORT = parseInt(process.env.DOT_DASH_PORT ?? '7765', 10);
const FRONTEND_DIR = join(__dirname, '..', '..', 'frontend', 'dist');

const sessions = new SessionManager();
const broadcaster = new Broadcaster();
const token = loadOrCreateToken();

// Start file watcher
createWatcher(sessions, (_sessionId, event) => {
  broadcaster.send({ type: 'transcript_event', payload: event });
});

const app = new Hono();
const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });

// Auth middleware for /api/*
app.use('/api/*', async (c, next) => {
  const authHeader = c.req.header('Authorization');
  const queryToken = c.req.query('token');
  const candidate = authHeader?.replace('Bearer ', '') ?? queryToken ?? '';
  if (!validateToken(candidate)) {
    return c.json({ error: 'Unauthorized' }, 401);
  }
  return next();
});

// Internal routes (localhost only)
app.post('/internal/session/register', async (c) => {
  const body = await c.req.json<{ session_id: string; cwd: string; pid?: number }>();
  const session = sessions.register(body.session_id, body.cwd, body.pid ?? 0);
  broadcaster.send({ type: 'session_registered', payload: session });
  return c.json({ ok: true, session });
});

app.post('/internal/session/deregister', async (c) => {
  const body = await c.req.json<{ session_id: string }>();
  sessions.deregister(body.session_id);
  const session = sessions.get(body.session_id);
  broadcaster.send({ type: 'session_stopped', payload: { sessionId: body.session_id, session } });
  return c.json({ ok: true });
});

app.get('/internal/inject/:sessionId', (c) => {
  const sessionId = c.req.param('sessionId');
  const item = sessions.dequeueInjection(sessionId);
  return c.json({ message: item?.message ?? null });
});

// REST API
app.get('/api/health', (c) => {
  return c.json({
    status: 'ok',
    sessions: sessions.getAll().length,
    clients: broadcaster.size(),
    token_file: '~/.claude/dot-dash/token',
  });
});

app.get('/api/sessions', (c) => {
  return c.json(sessions.getAll());
});

app.get('/api/sessions/:id', (c) => {
  const session = sessions.get(c.req.param('id'));
  if (!session) return c.json({ error: 'Not found' }, 404);
  return c.json(session);
});

app.delete('/api/sessions/:id', (c) => {
  sessions.deregister(c.req.param('id'));
  broadcaster.send({ type: 'session_stopped', payload: { sessionId: c.req.param('id') } });
  return c.json({ ok: true });
});

app.post('/api/sessions/:id/inject', async (c) => {
  const body = await c.req.json<{ message: string }>();
  if (!body.message) return c.json({ error: 'message required' }, 400);
  sessions.enqueueInjection(c.req.param('id'), body.message);
  return c.json({ ok: true });
});

// WebSocket
app.get(
  '/ws',
  upgradeWebSocket((c) => {
    const queryToken = c.req.query('token') ?? '';
    return {
      onOpen(_, ws) {
        if (!validateToken(queryToken)) {
          ws.close(1008, 'Unauthorized');
          return;
        }
        broadcaster.add(ws as unknown as Parameters<typeof broadcaster.add>[0]);
        const snapshot: WsMessage = {
          type: 'sessions_snapshot',
          payload: sessions.getAll(),
        };
        ws.send(JSON.stringify(snapshot));
      },
      onClose(_, ws) {
        broadcaster.remove(ws as unknown as Parameters<typeof broadcaster.remove>[0]);
      },
      onError(_, ws) {
        broadcaster.remove(ws as unknown as Parameters<typeof broadcaster.remove>[0]);
      },
    };
  }),
);

// Static files — serve frontend build
app.use('/*', serveStatic({ root: FRONTEND_DIR }));

// Start server
const server = serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`dot-dash server running at http://localhost:${PORT}`);
  console.log(`Token: ${token}`);
  console.log(`Dashboard: http://localhost:${PORT}`);
  console.log(`WebSocket: ws://localhost:${PORT}/ws?token=${token}`);
});

injectWebSocket(server);
