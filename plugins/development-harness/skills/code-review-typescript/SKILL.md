---
name: code-review-typescript
description: Provides TypeScript-specific code review patterns covering strict mode, ESM, type safety, branded types, discriminated unions, async patterns, runtime safety, and common anti-patterns. Activates on detection of tsconfig.json, *.ts, or *.tsx files during code review — loaded automatically by dh:code-reviewer.
user-invocable: false
---

# TypeScript Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `tsconfig.json`, `*.ts`, or `*.tsx` files are detected.

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria. Also apply Node.js checks for Node
execution and Web checks for browser rendering, including TSX; language checks do not replace
runtime checks.

## Strict Mode

- Apply the project's active compiler gates. Prefer strict checking for new projects; do not require a configuration migration solely to match a default.
- Inspect optional-property and indexed-access behavior for unsupported `undefined` values; establish the affected contract before recommending stronger compiler flags such as `exactOptionalPropertyTypes` or `noUncheckedIndexedAccess`.
- Investigate `@ts-ignore` and its justification: identify the diagnostic being hidden and whether the invariant is established elsewhere. An explanation alone does not prove safety.
- `@ts-expect-error` is preferred over `@ts-ignore` — it fails if the error goes away

## Type Safety

- Trace `any` and unchecked assertions to the dynamic boundary and their consumers; report unsupported assumptions that escape into typed code.
- Distinguish assertions over unvalidated external input from internal refinements supported by construction or an established invariant. Do not require runtime parsing solely to justify every `as` expression.
- `unknown` is the correct type for values from external sources — validate before narrowing, not after
- Choose types for the actual contract: `object`, a record, and a named interface describe different guarantees. Replacing `any` with another broad type alone does not validate external data.
- For non-null assertions (`value!`), verify why null is impossible on the relevant path; a comment is a claim to check, not sufficient evidence by itself.

## Discriminated Unions Over Booleans

- When multiple flags encode mutually exclusive states, check whether callers can construct or observe an invalid combination. Use a discriminated union when it expresses that contract; independent boolean properties need not become a state machine.
- Inspect transitions as well as the declared type; a state representation must preserve the supported loading, failure, and success behavior.

```typescript
// WRONG: boolean flags allow impossible states
interface State {
  isLoading: boolean;
  isError: boolean;
  data: User | null;
}

// RIGHT: discriminated union — impossible states are unrepresentable
type State =
  | { status: "loading" }
  | { status: "error"; error: Error }
  | { status: "success"; data: User };
```

## Branded Types

- Inspect semantically distinct primitives for consequential interchange at call sites. Recommend branded types or the project's existing domain representation when it prevents a demonstrated class of mix-ups.
- `UserId` and `OrderId` are both `string` at runtime — without brands, they are interchangeable to the type checker

```typescript
type UserId = string & { readonly _brand: "UserId" };
type OrderId = string & { readonly _brand: "OrderId" };

function makeUserId(id: string): UserId {
  return id as UserId;
}
```

## ESM

- Check `require()` and `import` against the project's supported runtime, package/module configuration, and emitted code; preserve a coherent CommonJS or ESM design.
- Named exports are preferred over default exports — easier to refactor and search
- Apply the project's type-only import rules and verify that emitted imports do not request runtime values that do not exist.
- Dynamic `import()` must be typed with the expected module shape

## Async Patterns

- Verify async results are awaited, returned to a responsible caller, or deliberately detached with rejection handling; report lost completion or failure signals at the actual consumer.
- Before recommending concurrency for sequential `await`, check ordering, rate limits, resource bounds, and failure/cancellation semantics. Use bounded concurrency or `Promise.all` only when the operation's contract supports it and there is a demonstrated benefit.
- Identify who owns rejection handling. Propagating a promise to a caller is valid when that caller handles the failure contract; a detached promise needs its own explicit policy.

## Runtime Safety

- Validate user-controlled input at its trust boundary with a schema or equivalent guard that establishes the required contract; a raw `as UserType` cast on external data establishes no runtime evidence.
- Trace parsed external data to validation before trusted use; a `JSON.parse(text) as MyType` cast alone does not establish the required shape.
- Validate environment values required by the selected execution mode before dependent work; trace assertions such as `process.env.API_KEY!` to the relevant guard and failure path.

## `satisfies` Operator

- `satisfies` is preferred over explicit type annotations for config objects and record literals — preserves the literal type while validating against the declared type
- Use when you want both type checking AND the narrowed type available downstream

```typescript
// RIGHT: satisfies preserves literal types
const config = {
  port: 3000,
  host: "localhost",
} satisfies ServerConfig;
// Check the inferred property types; satisfies validates compatibility.
```

## Anti-Patterns

```typescript
// Unchecked boundary: the required event shape is not established.
function process(data: any) { ... }

// RIGHT: specific type or documented any
function process(data: unknown) {
  if (!isUserEvent(data)) throw new TypeError("Expected UserEvent");
  ...
}

// WRONG: floating promise
sendMetrics(event);

// RIGHT: awaited, or deliberately detached with rejection handling
void sendMetrics(event).catch(reportMetricsFailure); // best-effort telemetry
// or
await sendMetrics(event);
```
