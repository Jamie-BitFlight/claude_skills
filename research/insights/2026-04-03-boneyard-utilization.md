# Utilization Proposals: Boneyard

**Research entry**: ../developer-tools/boneyard.md
**Generated**: 2026-04-03
**Integration surfaces found**: 2 (NPM SDK | CLI tool)
**Proposals written**: 1
**Skipped**: 1 — localhost-only app with no persistent loading states

---

## Utilization 1: dot-dash frontend → Boneyard skeleton screens

**Research entry**: ./research/developer-tools/boneyard.md
**Caller**: plugins/dot-dash/frontend/src/components/SessionList.tsx, plugins/dot-dash/frontend/src/components/Transcript.tsx
**Integration mechanism**: NPM dependency (`boneyard-js`)
**Replaces or adds**: Adds placeholder rendering while WebSocket data streams in
**Setup cost**: Low (npm install, CLI build integration, component wrapping)
**Integration surface**: `npm install boneyard-js`, `<Skeleton>` component from `boneyard-js/react`, `npx boneyard-js build` CLI

### Why this caller

The `dot-dash` frontend connects to Claude Code session data via WebSocket. When the page first loads or when a new session is selected, the user sees empty state placeholders (`"No sessions registered"` in SessionList, `"Select a session to view transcript"` in Transcript). During the async data stream, there is a perceptual delay before the SessionList populates with cards and the Transcript fills with events.

Currently, the loading experience is minimal — the user sees either empty state text or no visual feedback until data arrives. Boneyard would add pixel-perfect skeleton screens that match the final layout exactly, eliminating perceived jank and providing visual assurance that data is loading (via the pulse animation on bones).

The App.tsx reducer dispatches `set_sessions` and `add_event` actions as WebSocket messages arrive. Wrapping the SessionList and Transcript children with `<Skeleton loading={isLoading}>` would show bones until the first batch of data arrives, then switch to real content. Since the app state tracks `sessions` (initially `[]`) and `events` (initially empty Map), the caller can derive a `loading` state from `sessions.length === 0` or by tracking a separate `initialLoadInProgress` flag in the reducer.

### Integration sketch

**1. Install dependency:**
```bash
npm install boneyard-js
```

**2. Wrap SessionList in App.tsx (lines 149–153):**
```tsx
import { Skeleton } from 'boneyard-js/react'

// In App component:
const isLoadingInitial = state.wsConnected && state.sessions.length === 0

<Skeleton
  name="session-list"
  loading={isLoadingInitial}
  color="rgba(0,0,0,0.08)"
  darkColor="rgba(255,255,255,0.06)"
>
  <SessionList
    sessions={state.sessions}
    selectedId={state.selectedId}
    onSelect={(id) => dispatch({ type: 'select', id })}
  />
</Skeleton>
```

**3. Wrap Transcript in App.tsx (line 154):**
```tsx
<Skeleton
  name="transcript"
  loading={!!state.selectedId && state.events.get(state.selectedId)?.length === 0}
>
  <Transcript sessionId={state.selectedId} events={selectedEvents} />
</Skeleton>
```

**4. Build bones once (one-time dev task):**
```bash
cd plugins/dot-dash/frontend
npm run dev  # Start dev server in one terminal
npx boneyard-js build http://localhost:5173  # In another terminal
npm run build  # Rebuild for production
```

The CLI writes `src/bones/registry.ts` and per-component bone files. Import the registry in the frontend entry point:
```tsx
// src/main.tsx
import './bones/registry'  // Populates the in-memory bones registry
import { App } from './App'
```

**5. No additional app code changes are needed beyond steps 2–4** — after wrapping `SessionList` and `Transcript` with `<Skeleton>` and importing `./bones/registry` in `src/main.tsx`, the `<Skeleton>` component auto-resolves bones by name and uses `ResizeObserver` to track responsive behavior automatically.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| .claude/agents/* | Agents are reasoning/workflow tools, not UI rendering components. None generate or manage React components at runtime. |
| .claude/skills/* | Skills provide instructions and documentation; they do not render UI or consume WebSocket data. Boneyard is a runtime UI library, not a skill pattern. |
| .claude/rules/* | Rules are static documentation. Boneyard requires dynamic app state and interactive rendering. |
| plugins/dot-dash/server/ | Backend MCP server; Boneyard is a client-side React library. Integration would have no effect. |

---

## Scope Notes

**Why only SessionList and Transcript, not Controls?**

The Controls component (lines 155–158 in App.tsx) operates on selected session state. It does not render a list or stream of data — it displays a single action button. There is no perceptual delay or loading phase here; Boneyard's value is in masking async data arrival, not single-state rendering. Skipped.

**Why no integration in non-React systems?**

The codebase contains no other frontend applications. The monorepo is primarily CLI tooling, agents, and skills — all server-side. The dot-dash frontend is the only consumer of real-time data with user-facing loading delays.
