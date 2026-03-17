# TypeScript MCP Server Implementation Guide

Complete guide for implementing MCP servers using the MCP TypeScript SDK, covering project structure, server setup, tool registration, Zod validation, error handling, and production deployment.

## Server Naming Convention

RULE: The model must follow Node/TypeScript naming pattern

PATTERN: `{service}-mcp-server` (lowercase with hyphens)

EXAMPLES: `github-mcp-server`, `jira-mcp-server`, `stripe-mcp-server`

CONSTRAINTS:

- The model must use general names (not tied to specific features)
- The model must avoid version numbers or dates
- The model must choose names descriptive of the service/API being integrated

## Project Structure

REQUIRED_STRUCTURE:

<eg>
{service}-mcp-server/
├── package.json
├── tsconfig.json
├── README.md
├── src/
│   ├── index.ts          # Main entry point with McpServer initialization
│   ├── types.ts          # TypeScript type definitions and interfaces
│   ├── tools/            # Tool implementations (one file per domain)
│   ├── services/         # API clients and shared utilities
│   ├── schemas/          # Zod validation schemas
│   └── constants.ts      # Shared constants (API_URL, DEFAULT_LIMIT, etc.)
└── dist/                 # Built JavaScript files (entry point: dist/index.js)
</eg>

## Key Imports

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import axios, { AxiosError } from "axios";
```

## Server Initialization

```typescript
const server = new McpServer({
  name: "service-mcp-server",
  version: "1.0.0",
});
```

## Tool Implementation

### Tool Naming

RULE: The model must use snake_case for tool names

PATTERN: `{service}_{action}_{resource}`

EXAMPLES:

- "slack_send_message" (not just "send_message")
- "github_create_issue" (not just "create_issue")
- "asana_list_tasks" (not just "list_tasks")

### Tool Registration Pattern

RULE: The model must use `registerTool` method with complete configuration

CONSTRAINTS:

- The model must explicitly provide `title`, `description`, `inputSchema`, and `annotations`
- The model must use Zod schemas for `inputSchema` (not JSON schema)
- The model must not rely on JSDoc comments for automatic extraction
- The model must type all parameters and return values explicitly

### Complete Tool Example

```typescript
import { z } from "zod";

// Define enum for response format
enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json",
}

// Zod schema for input validation
const UserSearchInputSchema = z
  .object({
    query: z
      .string()
      .min(2, "Query must be at least 2 characters")
      .max(200, "Query must not exceed 200 characters")
      .describe("Search string to match against names/emails"),
    limit: z.number().int().min(1).max(100).default(20).describe("Maximum results to return"),
    offset: z.number().int().min(0).default(0).describe("Number of results to skip for pagination"),
    response_format: z
      .nativeEnum(ResponseFormat)
      .default(ResponseFormat.MARKDOWN)
      .describe("Output format: 'markdown' for human-readable or 'json' for machine-readable"),
  })
  .strict();

// Type definition from Zod schema
type UserSearchInput = z.infer<typeof UserSearchInputSchema>;

server.registerTool(
  "example_search_users",
  {
    title: "Search Example Users",
    description: `Search for users in the Example system by name, email, or team.

This tool searches across all user profiles in the Example platform, supporting partial matches and various search filters. It does NOT create or modify users, only searches existing ones.

Args:
  - query (string): Search string to match against names/emails
  - limit (number): Maximum results to return, between 1-100 (default: 20)
  - offset (number): Number of results to skip for pagination (default: 0)
  - response_format ('markdown' | 'json'): Output format (default: 'markdown')

Returns:
  For JSON format: Structured data with schema:
  {
    "total": number,           // Total number of matches found
    "count": number,           // Number of results in this response
    "offset": number,          // Current pagination offset
    "users": [
      {
        "id": string,          // User ID (e.g., "U123456789")
        "name": string,        // Full name (e.g., "John Doe")
        "email": string,       // Email address
        "team": string,        // Team name (optional)
        "active": boolean      // Whether user is active
      }
    ],
    "has_more": boolean,       // Whether more results are available
    "next_offset": number      // Offset for next page (if has_more is true)
  }

Examples:
  - Use when: "Find all marketing team members" -> params with query="team:marketing"
  - Use when: "Search for John's account" -> params with query="john"
  - Don't use when: You need to create a user (use example_create_user instead)

Error Handling:
  - Returns "Error: Rate limit exceeded" if too many requests (429 status)
  - Returns "No users found matching '<query>'" if search returns empty`,
    inputSchema: UserSearchInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true,
    },
  },
  async (params: UserSearchInput) => {
    try {
      // Input validation is handled by Zod schema
      // Make API request using validated parameters
      const data = await makeApiRequest<any>("users/search", "GET", undefined, {
        q: params.query,
        limit: params.limit,
        offset: params.offset,
      });

      const users = data.users || [];
      const total = data.total || 0;

      if (!users.length) {
        return {
          content: [
            {
              type: "text",
              text: `No users found matching '${params.query}'`,
            },
          ],
        };
      }

      // Format response based on requested format
      let result: string;

      if (params.response_format === ResponseFormat.MARKDOWN) {
        // Human-readable markdown format
        const lines: string[] = [`# User Search Results: '${params.query}'`, ""];
        lines.push(`Found ${total} users (showing ${users.length})`);
        lines.push("");

        for (const user of users) {
          lines.push(`## ${user.name} (${user.id})`);
          lines.push(`- **Email**: ${user.email}`);
          if (user.team) {
            lines.push(`- **Team**: ${user.team}`);
          }
          lines.push("");
        }

        result = lines.join("\n");
      } else {
        // Machine-readable JSON format
        const response: any = {
          total,
          count: users.length,
          offset: params.offset,
          users: users.map((user: any) => ({
            id: user.id,
            name: user.name,
            email: user.email,
            ...(user.team ? { team: user.team } : {}),
            active: user.active ?? true,
          })),
        };

        // Add pagination info if there are more results
        if (total > params.offset + users.length) {
          response.has_more = true;
          response.next_offset = params.offset + users.length;
        }

        result = JSON.stringify(response, null, 2);
      }

      return {
        content: [
          {
            type: "text",
            text: result,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: handleApiError(error),
          },
        ],
      };
    }
  },
);
```

## Zod Schemas for Input Validation

RULE: The model must use Zod for runtime type validation

### Basic Schema Patterns

```typescript
import { z } from "zod";

// Basic schema with validation
const CreateUserSchema = z
  .object({
    name: z.string().min(1, "Name is required").max(100, "Name must not exceed 100 characters"),
    email: z.string().email("Invalid email format"),
    age: z
      .number()
      .int("Age must be a whole number")
      .min(0, "Age cannot be negative")
      .max(150, "Age cannot be greater than 150"),
  })
  .strict(); // Use .strict() to forbid extra fields

// Enums
enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json",
}

const SearchSchema = z.object({
  response_format: z.nativeEnum(ResponseFormat).default(ResponseFormat.MARKDOWN).describe("Output format"),
});

// Optional fields with defaults
const PaginationSchema = z.object({
  limit: z.number().int().min(1).max(100).default(20).describe("Maximum results to return"),
  offset: z.number().int().min(0).default(0).describe("Number of results to skip"),
});
```

## Response Format Options

RULE: The model must support multiple output formats for flexibility

### Markdown Format

CHARACTERISTICS:

- Use headers, lists, and formatting for clarity
- Convert timestamps to human-readable format
- Show display names with IDs in parentheses
- Omit verbose metadata
- Group related information logically

### JSON Format

CHARACTERISTICS:

- Return complete, structured data suitable for programmatic processing
- Include all available fields and metadata
- Use consistent field names and types

## Pagination Implementation

RULE: The model must implement pagination for tools that list resources

```typescript
const ListSchema = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0),
});

async function listItems(params: z.infer<typeof ListSchema>) {
  const data = await apiRequest(params.limit, params.offset);

  const response = {
    total: data.total,
    count: data.items.length,
    offset: params.offset,
    items: data.items,
    has_more: data.total > params.offset + data.items.length,
    next_offset: data.total > params.offset + data.items.length ? params.offset + data.items.length : undefined,
  };

  return JSON.stringify(response, null, 2);
}
```

## Large Response Handling

RULE: The model must give callers control over response size — never silently truncate

CONSTRAINT: Do NOT introduce hardcoded character limits (e.g., `CHARACTER_LIMIT = 25000`) that silently drop data. Arbitrary truncation removes the caller's ability to read what they need and causes silent data loss. This is explicitly prohibited by the repository's "No Invented Limits" policy.

CORRECT APPROACH: Expose `offset` and `limit` parameters so the caller controls the window. When a response is paginated, always report `total`, `count`, `offset`, `has_more`, and `next_offset` so the caller knows how to retrieve the rest.

```typescript
// At module level in constants.ts
export const DEFAULT_PAGE_LIMIT = 20; // Default page size — caller may override via 'limit' param

async function searchTool(params: SearchInput) {
  // Use caller-controlled pagination instead of silent truncation
  const data = await fetchData({
    limit: params.limit ?? DEFAULT_PAGE_LIMIT,
    offset: params.offset ?? 0,
  });

  const response = {
    total: data.total,
    count: data.items.length,
    offset: params.offset ?? 0,
    items: data.items,
    has_more: data.total > (params.offset ?? 0) + data.items.length,
    next_offset:
      data.total > (params.offset ?? 0) + data.items.length
        ? (params.offset ?? 0) + data.items.length
        : undefined,
  };

  // If the caller requests a very large page and the upstream API returns a
  // partial result, surface that fact explicitly — never silently omit data.
  if (data.items.length < (params.limit ?? DEFAULT_PAGE_LIMIT) && response.has_more) {
    response.warning =
      `Upstream returned ${data.items.length} of ${params.limit ?? DEFAULT_PAGE_LIMIT} requested items. ` +
      `Use next_offset (${response.next_offset}) to continue.`;
  }

  return JSON.stringify(response, null, 2);
}
```

## Error Handling

RULE: The model must provide clear, actionable error messages

```typescript
import axios, { AxiosError } from "axios";

function handleApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response) {
      switch (error.response.status) {
        case 404:
          return "Error: Resource not found. Please check the ID is correct.";
        case 403:
          return "Error: Permission denied. You don't have access to this resource.";
        case 429:
          return "Error: Rate limit exceeded. Please wait before making more requests.";
        default:
          return `Error: API request failed with status ${error.response.status}`;
      }
    } else if (error.code === "ECONNABORTED") {
      return "Error: Request timed out. Please try again.";
    }
  }
  return `Error: Unexpected error occurred: ${error instanceof Error ? error.message : String(error)}`;
}
```

## Shared Utilities

RULE: The model must extract common functionality into reusable functions

```typescript
// Shared API request function
async function makeApiRequest<T>(
  endpoint: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  data?: any,
  params?: any,
): Promise<T> {
  try {
    const response = await axios({
      method,
      url: `${API_BASE_URL}/${endpoint}`,
      data,
      params,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    });
    return response.data;
  } catch (error) {
    throw error;
  }
}
```

## TypeScript Best Practices

RULE: The model must follow TypeScript strict mode standards

CONSTRAINTS:

- The model must enable strict mode in tsconfig.json
- The model must define interfaces for all data structures
- The model must avoid `any` type - use proper types or `unknown`
- The model must use Zod schemas to validate external data
- The model must create type guard functions for complex type checking
- The model must always use try-catch with proper error type checking
- The model must use optional chaining (`?.`) and nullish coalescing (`??`)

### Type Safety Example

```typescript
// Good: Type-safe with Zod and interfaces
interface UserResponse {
  id: string;
  name: string;
  email: string;
  team?: string;
  active: boolean;
}

const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  team: z.string().optional(),
  active: z.boolean(),
});

type User = z.infer<typeof UserSchema>;

async function getUser(id: string): Promise<User> {
  const data = await apiCall(`/users/${id}`);
  return UserSchema.parse(data); // Runtime validation
}

// Bad: Using any
async function getUser(id: string): Promise<any> {
  return await apiCall(`/users/${id}`); // No type safety
}
```

## Package Configuration

### package.json

```json
{
  "name": "{service}-mcp-server",
  "version": "1.0.0",
  "description": "MCP server for {Service} API integration",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "clean": "rm -rf dist"
  },
  "engines": {
    "node": ">=18"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.6.1",
    "axios": "^1.7.9",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "tsx": "^4.19.2",
    "typescript": "^5.7.2"
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "allowSyntheticDefaultImports": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## Building and Running

RULE: The model must always build TypeScript code before running

```bash
# Build the project
npm run build

# Run the server
npm start

# Development with auto-reload
npm run dev
```

CONSTRAINT: The model must ensure `npm run build` completes successfully before considering implementation complete

## Advanced Features

### Resource Registration

```typescript
import { ResourceTemplate } from "@modelcontextprotocol/sdk/types.js";

// Register a resource with URI template
server.registerResource(
  {
    uri: "file://documents/{name}",
    name: "Document Resource",
    description: "Access documents by name",
    mimeType: "text/plain",
  },
  async (uri: string) => {
    // Extract parameter from URI
    const match = uri.match(/^file:\/\/documents\/(.+)$/);
    if (!match) {
      throw new Error("Invalid URI format");
    }

    const documentName = match[1];
    const content = await loadDocument(documentName);

    return {
      contents: [
        {
          uri,
          mimeType: "text/plain",
          text: content,
        },
      ],
    };
  },
);
```

### Transport Options

```typescript
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";

// Stdio transport (default - for CLI tools)
const stdioTransport = new StdioServerTransport();
await server.connect(stdioTransport);

// SSE transport (for real-time web updates)
const sseTransport = new SSEServerTransport("/message", response);
await server.connect(sseTransport);
```

## Code Composability

RULE: The model must prioritize code reuse and avoid duplication

CONSTRAINTS:

- The model must extract common functionality into reusable helper functions
- The model must build shared API clients for HTTP requests
- The model must centralize error handling logic
- The model must extract business logic into dedicated composable functions
- The model must share markdown or JSON formatting functionality
- The model must never copy-paste similar code between tools

## Quality Checklist

STRATEGIC_DESIGN:

- [ ] Tools enable complete workflows, not just API endpoint wrappers
- [ ] Tool names reflect natural task subdivisions
- [ ] Response formats optimize for agent context efficiency
- [ ] Human-readable identifiers used where appropriate
- [ ] Error messages guide agents toward correct usage

IMPLEMENTATION_QUALITY:

- [ ] Most important and valuable tools implemented
- [ ] All tools registered using `registerTool` with complete configuration
- [ ] All tools include `title`, `description`, `inputSchema`, and `annotations`
- [ ] Annotations correctly set
- [ ] All tools use Zod schemas with `.strict()` enforcement
- [ ] Error messages are clear, actionable, and educational

TYPESCRIPT_QUALITY:

- [ ] TypeScript interfaces defined for all data structures
- [ ] Strict TypeScript enabled in tsconfig.json
- [ ] No use of `any` type
- [ ] All async functions have explicit Promise<T> return types
- [ ] Error handling uses proper type guards

PROJECT_CONFIGURATION:

- [ ] Package.json includes all necessary dependencies
- [ ] Build script produces working JavaScript in dist/ directory
- [ ] Main entry point properly configured as dist/index.js
- [ ] Server name follows format: `{service}-mcp-server`
- [ ] tsconfig.json properly configured with strict mode

CODE_QUALITY:

- [ ] Pagination properly implemented where applicable
- [ ] Large responses use caller-controlled `offset`/`limit` pagination — no hardcoded truncation
- [ ] Filtering options provided for potentially large result sets
- [ ] All network operations handle timeouts and connection errors
- [ ] Common functionality extracted into reusable functions

TESTING_AND_BUILD:

- [ ] `npm run build` completes successfully without errors
- [ ] dist/index.js created and executable
- [ ] Server runs successfully
- [ ] All imports resolve correctly
- [ ] Sample tool calls work as expected

## Summary

TypeScript MCP server development requires:

- Strict typing with TypeScript and Zod validation
- Complete tool configuration with explicit schemas
- Proper error handling and resource cleanup
- Code composability and reusability
- Production-ready build process

Follow these guidelines to create type-safe, maintainable MCP servers in TypeScript.

## Sources

- [MCP TypeScript SDK (modelcontextprotocol/typescript-sdk)](https://github.com/modelcontextprotocol/typescript-sdk) (accessed 2026-02-22)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/) (accessed 2026-02-22)
- [FastMCP Official Documentation](https://gofastmcp.com/) (accessed 2026-02-22)
- [Zod Schema Validation Library](https://github.com/colinhacks/zod) (accessed 2026-02-22)
