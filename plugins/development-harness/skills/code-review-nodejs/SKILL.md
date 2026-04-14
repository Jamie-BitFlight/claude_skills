---
name: code-review-nodejs
description: Applies Node.js-specific code review patterns for async I/O, streams, security, process management, and dependency hygiene. Use when reviewing Node.js server code, route handlers, middleware, or any JavaScript file alongside package.json without TypeScript. Triggers on sync I/O in request paths, missing stream backpressure, process.exit misuse, eval/exec injection risks, wildcard version ranges, missing lockfiles, EventEmitter cleanup gaps, and unvalidated environment variables at startup.
user-invocable: false
---

# Node.js Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `package.json` and `*.js`/`*.mjs` files are detected (without TypeScript).

## Synchronous I/O in Request Path

- `fs.readFileSync`, `fs.writeFileSync`, `execSync`, `spawnSync` in any function called during request handling are blocking findings
- Synchronous I/O blocks the event loop and degrades all concurrent requests
- All file system operations in server code must use the async variants or `fs/promises`

```javascript
// WRONG: blocks event loop
app.get("/config", (req, res) => {
  const config = fs.readFileSync("./config.json", "utf8");
  res.json(JSON.parse(config));
});

// RIGHT: non-blocking
app.get("/config", async (req, res) => {
  const config = await fs.promises.readFile("./config.json", "utf8");
  res.json(JSON.parse(config));
});
```

## Stream Backpressure

- Piping streams without handling backpressure is a blocking finding for high-throughput paths
- `readable.pipe(writable)` handles backpressure automatically — prefer it over manual `data` event listeners
- Manual `data` event listeners must check `writable.write()` return value and pause the readable when it returns `false`

## Process Exit

- `process.exit()` is only acceptable in CLI entrypoints — it is a blocking finding in library code, route handlers, or middleware
- Unhandled `process.on("uncaughtException")` that calls `process.exit()` without logging the error is a blocking finding

## Security

- `eval()` is a blocking finding everywhere — no exceptions
- `new Function(code)` with user-controlled `code` is a blocking finding
- Shell arguments constructed by string concatenation with user input before passing to `exec` or `spawn` are a blocking finding
- `execFile` is required over `exec` when calling external programs — `exec` invokes a shell and is vulnerable to injection
- User-controlled values used as file paths must be validated against an allowed base directory (path traversal)

```javascript
// WRONG: shell injection vector
exec(`convert ${userInput} output.png`);

// RIGHT: no shell, explicit args
execFile("convert", [userInput, "output.png"]);
```

## Dependency Hygiene

- `*` version ranges in `package.json` are a blocking finding — they produce non-reproducible installs
- `^` ranges are acceptable; `~` is preferred for stricter patch-level pinning
- `package-lock.json` or `yarn.lock` must be committed — without a lockfile, versions are not reproducible in CI
- Dev-only dependencies must be in `devDependencies`, not `dependencies` — they inflate production bundle size

## Event Emitter Cleanup

- `EventEmitter.on()` listeners added in component/connection lifecycle must be removed when that lifecycle ends
- Missing `removeListener` or `off()` calls are a blocking finding when the emitter outlives the listener
- Use `EventEmitter.once()` for one-shot listeners to avoid manual cleanup

## Environment Variables

- All required environment variables must be validated at startup, before the server begins accepting requests
- `process.env.SOME_VAR!` without validation is a blocking finding — the app will fail with a confusing error at runtime rather than a clear startup message
- Provide a `.env.example` file listing all required variables — checked in, never containing real values

## `execFile` Over `exec`

```javascript
// WRONG: shell injection risk
exec(`git log --oneline ${branch}`);

// RIGHT: explicit argument array, no shell
execFile("git", ["log", "--oneline", branch], (err, stdout) => { ... });
```

## Anti-Patterns

```javascript
// WRONG: missing error handling on EventEmitter
server.on("connection", (socket) => {
  socket.on("data", handleData);
  // missing: socket.on("end", cleanup) and removeListener
});

// WRONG: unvalidated env at use site
const apiKey = process.env.API_KEY;
fetch(url, { headers: { Authorization: apiKey } }); // null if unset

// RIGHT: validate at startup
if (!process.env.API_KEY) {
  console.error("FATAL: API_KEY environment variable is required");
  process.exit(1);
}
const apiKey = process.env.API_KEY;
```
