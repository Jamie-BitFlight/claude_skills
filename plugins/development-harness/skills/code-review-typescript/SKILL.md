---
name: code-review-typescript
description: Provides TypeScript-specific code review patterns covering strict mode, ESM, type safety, branded types, discriminated unions, async patterns, runtime safety, and common anti-patterns. Activates on detection of tsconfig.json, *.ts, or *.tsx files during code review — loaded automatically by dh:code-reviewer.
user-invocable: false
---

# TypeScript Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `tsconfig.json`, `*.ts`, or `*.tsx` files are detected.

## Strict Mode

- `tsconfig.json` must enable `strict: true` — this covers `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, and others
- `exactOptionalPropertyTypes: true` is required in new projects — prevents `undefined` from being assigned to optional properties
- `noUncheckedIndexedAccess: true` is required when indexing arrays or records — prevents silent `undefined` propagation
- Any `@ts-ignore` comment without an accompanying explanation comment is a blocking finding
- `@ts-expect-error` is preferred over `@ts-ignore` — it fails if the error goes away

## Type Safety

- `any` type without an explanatory comment is a blocking finding
- Type assertions (`as SomeType`) without runtime validation at the same boundary are a blocking finding
- `unknown` is the correct type for values from external sources — validate before narrowing, not after
- `object` as a type is not meaningful — use `Record<string, unknown>` or a specific interface
- Non-null assertions (`value!`) without a comment explaining why null is impossible are a blocking finding

## Discriminated Unions Over Booleans

- Multiple boolean flags encoding state are a blocking finding — model as a discriminated union instead
- State machine logic with `isLoading`, `isError`, `isSuccess` as separate booleans allows impossible combinations

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

- Domain primitives that are structurally identical but semantically distinct must use branded types to prevent mix-ups
- `UserId` and `OrderId` are both `string` at runtime — without brands, they are interchangeable to the type checker

```typescript
type UserId = string & { readonly _brand: "UserId" };
type OrderId = string & { readonly _brand: "OrderId" };

function makeUserId(id: string): UserId {
  return id as UserId;
}
```

## ESM

- `require()` calls are a blocking finding — use `import` syntax
- Named exports are preferred over default exports — easier to refactor and search
- `import type` must be used for type-only imports — prevents runtime errors and improves tree-shaking
- Dynamic `import()` must be typed with the expected module shape

## Async Patterns

- Floating promises (calling an async function without `await` or `.then()/.catch()`) are a blocking finding
- `Promise.all` is required for parallel independent async operations — sequential `await` in a loop is an anti-pattern when operations are independent
- `await` inside a `for` loop that processes independent items is a blocking finding
- Unhandled promise rejections must have explicit error handling at the call site

## Runtime Safety

- User-controlled input entering the system must be validated against a schema (zod, valibot, or equivalent) at the boundary — no raw `as UserType` casts on external data
- JSON.parse results must be validated before use — `JSON.parse(text) as MyType` is a blocking finding
- Environment variables must be validated at startup with specific error messages — `process.env.API_KEY!` without validation is a blocking finding

## `satisfies` Operator

- `satisfies` is preferred over explicit type annotations for config objects and record literals — preserves the literal type while validating against the declared type
- Use when you want both type checking AND the narrowed type available downstream

```typescript
// RIGHT: satisfies preserves literal types
const config = {
  port: 3000,
  host: "localhost",
} satisfies ServerConfig;
// config.port is typed as 3000, not number
```

## Anti-Patterns

```typescript
// WRONG: any without comment
function process(data: any) { ... }

// RIGHT: specific type or documented any
function process(data: unknown) {
  if (!isUserEvent(data)) throw new TypeError("Expected UserEvent");
  ...
}

// WRONG: floating promise
sendMetrics(event);

// RIGHT: awaited or explicitly fire-and-forget
void sendMetrics(event); // intentionally not awaited — best-effort telemetry
// or
await sendMetrics(event);
```
