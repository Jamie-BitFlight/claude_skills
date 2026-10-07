---
name: code-review-nodejs
description: Reviews Node.js runtime behavior in JavaScript or TypeScript, including server entrypoints, route handlers, middleware, streams, processes, dependencies, and environment configuration. Loads alongside language and CLI checks when applicable; investigates blocking I/O, backpressure, injection, lifecycle leaks, and misleading failure signals.
user-invocable: false
---

# Node.js Code Review Patterns

Load these checks when source, runtime entrypoints, or package scripts establish Node.js execution,
including JavaScript, TypeScript, CJS, and MJS. Apply TypeScript or CLI checks alongside them when
relevant; a `package.json` alone does not distinguish server code from a browser build.

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria.

## Synchronous I/O in Request Path

- Trace `fs.readFileSync`, `fs.writeFileSync`, `execSync`, or `spawnSync` to the active request/event-loop path and establish the blocking consequence or violated latency contract.
- Use async variants or `fs/promises` for work that must not block that path. Do not flag isolated startup/setup I/O solely because it is in a server file.

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

- Keep process termination at the application/CLI boundary that owns shutdown, including fatal startup failure. Report library, route, or middleware exits that unexpectedly terminate unrelated work or bypass required cleanup.
- Unhandled `process.on("uncaughtException")` that calls `process.exit()` without logging the error is a blocking finding

## Security

- Trace dynamic evaluation, including `eval()`, to its input authority and execution privileges; report untrusted-code execution or an explicit project prohibition.
- `new Function(code)` with user-controlled `code` is a blocking finding
- Trace user input into shell evaluation and command/option parsing. Distinguish shell interpolation from separate process arguments, and report the injection or unauthorized operation the actual call permits.
- Prefer `execFile` with separate arguments when no shell behavior is needed. For deliberate shell use, inspect interpolation and input authority rather than treating a trusted constant command as user-input injection.
- Constrain user-controlled paths to the resources authorized for the operation; verify allowed-root enforcement where the contract requires it and trace path traversal across that boundary.

```javascript
// WRONG: shell injection vector
exec(`convert ${userInput} output.png`);

// RIGHT: no shell, explicit args
execFile("convert", [userInput, "output.png"]);
```

## Dependency Hygiene

- Check version ranges against the target's dependency and release policy; trace wildcard ranges to the actual resolution/install behavior before claiming non-reproducibility.
- Verify the chosen package manager's lockfile and CI install mode preserve the required dependency resolution. Do not require an npm/yarn lockfile from a project using another supported package manager.
- Dev-only dependencies must be in `devDependencies`, not `dependencies`

## Event Emitter Cleanup

- `EventEmitter.on()` listeners added in component/connection lifecycle must be removed when that lifecycle ends
- Missing `removeListener` or `off()` calls are a blocking finding when the emitter outlives the listener
- Use `EventEmitter.once()` for one-shot listeners to avoid manual cleanup

## Environment Variables

- Validate configuration required for the selected execution mode before accepting work that depends on it. Do not require disabled optional features to supply credentials.
- Trace `process.env.SOME_VAR!` to the relevant validation and consumer; report a missing required value or unsupported assumption with its actual failure path.
- Provide a `.env.example` file listing all required variables — checked in, never containing real values

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
