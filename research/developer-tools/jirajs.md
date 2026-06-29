---
name: jira.js - JavaScript/TypeScript Client for Jira
description: jira.js is a comprehensive JavaScript and TypeScript client library for Atlassian Jira's REST API. It provides full coverage of Jira Cloud, Jira Server, and Jira Data Center APIs with strong...
license: MIT
metadata:
  topic: jirajs
  category: developer-tools
  source_url: https://mrrefactoring.github.io/jira.js/
  github: MrRefactoring/jira.js
  version: "v4.0.1"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

jira.js is a comprehensive JavaScript and TypeScript client library for Atlassian Jira's REST API. It provides full coverage of Jira Cloud, Jira Server, and Jira Data Center APIs with strong TypeScript typing, promise-based async/await support, and automatic request/response handling. The library abstracts the complexity of Jira's extensive API surface into a clean, intuitive interface.

**Core Value Proposition**: Enable developers to integrate Jira functionality into applications with type-safe, well-documented methods covering all Jira APIs (Core, Agile, ServiceDesk) without manual API endpoint construction.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Jira REST API has 500+ endpoints with complex parameters | Organized namespace structure with typed methods for every endpoint |
| Manual API request construction is error-prone | Abstracted request building with parameter validation |
| Authentication methods vary (Basic, OAuth, Token) | Unified authentication configuration supporting all methods |
| TypeScript definitions for Jira API are incomplete or outdated | Auto-generated types from official Jira API specifications |
| Different APIs for Cloud vs Server vs Data Center | Single interface with version detection and compatibility handling |
| Pagination handling requires manual implementation | Built-in pagination support with async iterators |
| API documentation scattered across Atlassian docs | Comprehensive documentation with examples for each method |
| Error handling varies across Jira API endpoints | Standardized error responses with detailed error messages |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,800+ | 2026-02-20 |
| npm Downloads/week | 150,000+ | 2026-02-20 |
| Contributors | 40+ | 2026-02-20 |
| Latest Release | v4.0.1 | 2026-02-20 |
| Primary Language | TypeScript | 2026-02-20 |
| API Coverage | 500+ endpoints | 2026-02-20 |
| TypeScript Support | Full types | 2026-02-20 |

---

## Key Features

### 1. Complete API Coverage

**Jira Platform REST API v3** (Cloud):
- Issues and issue fields
- Projects and project components
- Users and groups
- Workflows and workflow schemes
- Permissions and permission schemes
- Dashboards and filters
- Application properties
- Audit logs

**Jira Agile (Jira Software)** API:
- Boards (Scrum and Kanban)
- Sprints and sprint management
- Backlogs
- Epics
- Estimates and velocity
- Reports

**Jira Service Management** API:
- Service desks and queues
- Customer requests
- SLA tracking
- Organizations
- Knowledge base articles

**Jira Server/Data Center** APIs:
- Legacy API v2 support
- Server-specific endpoints
- Data Center clustering features

### 2. Type Safety

```typescript
import { Version3Client } from 'jira.js';

const client = new Version3Client({
  host: 'https://your-domain.atlassian.net',
  authentication: {
    basic: {
      email: 'user@example.com',
      apiToken: 'your-api-token'
    }
  }
});

// Fully typed responses
const issue = await client.issues.getIssue({ issueIdOrKey: 'PROJECT-123' });
// issue.fields is typed with Jira field types
console.log(issue.fields.summary); // TypeScript knows this is a string
```

### 3. Multiple Authentication Methods

**API Token** (Cloud - Recommended):

```typescript
authentication: {
  basic: {
    email: 'user@example.com',
    apiToken: 'ATATT3xFfGF0...'
  }
}
```

**OAuth 2.0** (Cloud):

```typescript
authentication: {
  oauth2: {
    accessToken: 'your-access-token'
  }
}
```

**Personal Access Token** (Server/Data Center):

```typescript
authentication: {
  personalAccessToken: 'your-pat-token'
}
```

**Basic Authentication** (Server/Data Center - Legacy):

```typescript
authentication: {
  basic: {
    username: 'admin',
    password: 'admin-password'
  }
}
```

### 4. Version-Specific Clients

```typescript
// Jira Cloud (API v3)
import { Version3Client } from 'jira.js';
const cloudClient = new Version3Client({ /* config */ });

// Jira Cloud (API v2)
import { Version2Client } from 'jira.js';
const v2Client = new Version2Client({ /* config */ });

// Agile API
import { AgileClient } from 'jira.js';
const agileClient = new AgileClient({ /* config */ });
```

### 5. Pagination Support

```typescript
// Automatic pagination handling
const issues = await client.issueSearch.searchForIssuesUsingJql({
  jql: 'project = PROJ',
  maxResults: 50,
  startAt: 0
});

// Paginate through all results
let startAt = 0;
const maxResults = 50;
let allIssues = [];

while (true) {
  const response = await client.issueSearch.searchForIssuesUsingJql({
    jql: 'project = PROJ',
    maxResults,
    startAt
  });

  allIssues.push(...response.issues);

  if (response.issues.length < maxResults) break;
  startAt += maxResults;
}
```

### 6. Middleware Support

```typescript
// Request/response interceptors
const client = new Version3Client({
  host: 'https://your-domain.atlassian.net',
  authentication: { /* ... */ },
  middlewares: [
    {
      onRequest: (config) => {
        console.log('Request:', config);
        return config;
      },
      onResponse: (response) => {
        console.log('Response:', response);
        return response;
      },
      onError: (error) => {
        console.error('Error:', error);
        throw error;
      }
    }
  ]
});
```

### 7. File Upload/Download

```typescript
// Upload attachment to issue
import fs from 'fs';

await client.issueAttachments.addAttachment({
  issueIdOrKey: 'PROJECT-123',
  attachment: fs.createReadStream('./document.pdf')
});

// Download attachment
const attachment = await client.issueAttachments.getAttachment({
  id: '10000'
});
```

---

## Technical Architecture

<eg>
Application Code
      |
      v
+------------------------------------------+
|           jira.js Client                 |
|  +------------------------------------+  |
|  |      Version-Specific Client       |  |
|  |  - Version3Client (Cloud v3)       |  |
|  |  - Version2Client (Cloud v2)       |  |
|  |  - AgileClient (Agile API)         |  |
|  |  - ServiceDeskClient (SM API)      |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |      Authentication Layer          |  |
|  |  - Basic (email + token)           |  |
|  |  - OAuth 2.0                       |  |
|  |  - Personal Access Token           |  |
|  |  - Token refresh handling          |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |      Request Builder               |  |
|  |  - URL construction                |  |
|  |  - Parameter validation            |  |
|  |  - Body serialization              |  |
|  |  - Multipart form data             |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |      Middleware Pipeline           |  |
|  |  - Request interceptors            |  |
|  |  - Response interceptors           |  |
|  |  - Error handlers                  |  |
|  |  - Retry logic                     |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |      HTTP Client (Axios)           |  |
|  |  - Connection pooling              |  |
|  |  - Timeout handling                |  |
|  |  - Automatic retries               |  |
|  +------------------------------------+  |
+------------------------------------------+
      |
      v
Jira REST API (Cloud/Server/Data Center)
</eg>

---

## Installation & Usage

### Installation

```bash
# npm
npm install jira.js

# yarn
yarn add jira.js

# pnpm
pnpm add jira.js
```

### Basic Usage - Jira Cloud

```typescript
import { Version3Client } from 'jira.js';

const client = new Version3Client({
  host: 'https://your-domain.atlassian.net',
  authentication: {
    basic: {
      email: 'your-email@example.com',
      apiToken: 'your-api-token'
    }
  }
});

// Get issue
const issue = await client.issues.getIssue({
  issueIdOrKey: 'PROJECT-123'
});

console.log(issue.fields.summary);
console.log(issue.fields.status.name);
```

### Create Issue

```typescript
const newIssue = await client.issues.createIssue({
  fields: {
    project: {
      key: 'PROJ'
    },
    summary: 'Issue created via jira.js',
    description: 'This is a test issue',
    issuetype: {
      name: 'Task'
    },
    priority: {
      name: 'Medium'
    }
  }
});

console.log(`Created issue: ${newIssue.key}`);
```

### Update Issue

```typescript
await client.issues.editIssue({
  issueIdOrKey: 'PROJECT-123',
  fields: {
    summary: 'Updated summary',
    description: 'Updated description'
  }
});
```

### Add Comment

```typescript
await client.issueComments.addComment({
  issueIdOrKey: 'PROJECT-123',
  body: {
    type: 'doc',
    version: 1,
    content: [
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: 'This is a comment added via jira.js'
          }
        ]
      }
    ]
  }
});
```

### Search Issues (JQL)

```typescript
const searchResults = await client.issueSearch.searchForIssuesUsingJql({
  jql: 'project = PROJ AND status = "In Progress"',
  fields: ['summary', 'status', 'assignee'],
  maxResults: 50
});

searchResults.issues.forEach(issue => {
  console.log(`${issue.key}: ${issue.fields.summary}`);
});
```

### Agile API - Sprint Management

```typescript
import { AgileClient } from 'jira.js';

const agileClient = new AgileClient({
  host: 'https://your-domain.atlassian.net',
  authentication: {
    basic: {
      email: 'your-email@example.com',
      apiToken: 'your-api-token'
    }
  }
});

// Get board
const board = await agileClient.board.getBoard({ boardId: 1 });

// Get active sprint
const sprints = await agileClient.board.getAllSprints({
  boardId: 1,
  state: 'active'
});

// Get sprint issues
const sprintIssues = await agileClient.sprint.getIssuesForSprint({
  sprintId: sprints.values[0].id
});
```

### Service Desk API

```typescript
import { ServiceDeskClient } from 'jira.js';

const serviceDeskClient = new ServiceDeskClient({
  host: 'https://your-domain.atlassian.net',
  authentication: {
    basic: {
      email: 'your-email@example.com',
      apiToken: 'your-api-token'
    }
  }
});

// Get service desks
const serviceDesks = await serviceDeskClient.servicedesk.getServiceDesks();

// Create customer request
const request = await serviceDeskClient.request.createCustomerRequest({
  serviceDeskId: '1',
  requestTypeId: '10',
  requestFieldValues: {
    summary: 'Need help with account',
    description: 'I cannot access my account'
  }
});
```

---

## Relevance to Claude Code Development

### Applications

1. **AI Agent Task Integration**: Agents can create, update, and track Jira issues programmatically for project management workflows
2. **Automated Issue Creation**: Claude Code could create Jira issues from conversation context (bugs found, features discussed, technical debt identified)
3. **Context Gathering**: Pull Jira issue context into Claude Code sessions to understand current project state
4. **Workflow Automation**: Automate transitions, assignments, and status updates based on code analysis or completion
5. **Sprint Planning**: AI-assisted sprint planning by analyzing issue complexity, dependencies, and team capacity

### Patterns Worth Adopting

1. **Namespace Organization**: jira.js organizes 500+ methods into logical namespaces (issues, projects, users) - applicable to large skill libraries
2. **Version-Specific Clients**: Separate clients for API versions prevents breaking changes - pattern for Claude Code plugin versioning
3. **TypeScript-First Design**: Generated types from API specs ensure accuracy - could generate skill types from YAML frontmatter
4. **Middleware Pattern**: Request/response interceptors enable logging, retries, error handling - applicable to MCP tool chains
5. **Authentication Abstraction**: Single config supports multiple auth methods - pattern for multi-provider MCP servers

### Integration Opportunities

1. **Jira MCP Server**: Create MCP server using jira.js for native Jira integration in Claude Code
2. **Issue Tracking Skill**: Skill that uses jira.js to link code changes to Jira issues automatically
3. **Project Context Tool**: Tool that fetches current sprint/backlog to inform AI about project priorities
4. **Automated Documentation**: Link generated docs to Jira epics/stories
5. **Quality Gate Integration**: Create Jira issues for failed tests, linting errors, or security vulnerabilities

### MCP Server Implementation Pattern

```typescript
// Example MCP server for Jira using jira.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { Version3Client } from 'jira.js';

const jiraClient = new Version3Client({
  host: process.env.JIRA_HOST,
  authentication: {
    basic: {
      email: process.env.JIRA_EMAIL,
      apiToken: process.env.JIRA_API_TOKEN
    }
  }
});

const server = new Server({
  name: 'jira-mcp',
  version: '1.0.0'
}, {
  capabilities: {
    tools: {}
  }
});

server.setRequestHandler('tools/list', async () => ({
  tools: [
    {
      name: 'jira_get_issue',
      description: 'Fetch Jira issue details by key or ID',
      inputSchema: {
        type: 'object',
        properties: {
          issueKey: { type: 'string', description: 'Issue key (e.g., PROJ-123)' }
        },
        required: ['issueKey']
      }
    },
    {
      name: 'jira_create_issue',
      description: 'Create new Jira issue',
      inputSchema: {
        type: 'object',
        properties: {
          project: { type: 'string', description: 'Project key' },
          summary: { type: 'string', description: 'Issue summary' },
          issueType: { type: 'string', description: 'Issue type (Task, Bug, Story)' }
        },
        required: ['project', 'summary', 'issueType']
      }
    },
    {
      name: 'jira_search_issues',
      description: 'Search issues using JQL',
      inputSchema: {
        type: 'object',
        properties: {
          jql: { type: 'string', description: 'JQL query string' },
          maxResults: { type: 'number', description: 'Maximum results', default: 50 }
        },
        required: ['jql']
      }
    }
  ]
}));

server.setRequestHandler('tools/call', async (request) => {
  switch (request.params.name) {
    case 'jira_get_issue': {
      const issue = await jiraClient.issues.getIssue({
        issueIdOrKey: request.params.arguments.issueKey
      });
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(issue, null, 2)
        }]
      };
    }
    // ... other tool implementations
  }
});
```

### Key Insight

jira.js demonstrates that comprehensive API client libraries can make complex external services accessible to AI agents. The type-safe, well-documented interface enables AI systems to interact with Jira without hallucinating API endpoints or parameters. This pattern applies to any external service integration: strong typing + clear documentation + logical organization = reliable AI tool usage.

---

## References

1. **Official Documentation**: <https://mrrefactoring.github.io/jira.js/> (accessed 2026-02-20)
2. **GitHub Repository**: <https://github.com/MrRefactoring/jira.js> (accessed 2026-02-20)
3. **npm Package**: <https://www.npmjs.com/package/jira.js> (accessed 2026-02-20)
4. **Jira Cloud REST API Documentation**: <https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/> (accessed 2026-02-20)
5. **Jira Agile REST API Documentation**: <https://developer.atlassian.com/cloud/jira/software/rest/intro/> (accessed 2026-02-20)
6. **Jira Service Management API**: <https://developer.atlassian.com/cloud/jira/service-desk/rest/intro/> (accessed 2026-02-20)

---

## Related Tools

| Tool | Relationship |
|------|--------------|
| [jira-client](https://www.npmjs.com/package/jira-client) | Older Jira client library (less active maintenance) |
| [node-jira](https://www.npmjs.com/package/node-jira) | Alternative Jira client (limited TypeScript support) |
| [atlassian-js-api](https://www.npmjs.com/package/atlassian-js-api) | Multi-product Atlassian client (Jira, Confluence, Bitbucket) |
| [@octokit/rest](https://www.npmjs.com/package/@octokit/rest) | Similar pattern for GitHub API |
| [gitlab](https://www.npmjs.com/package/gitlab) | Similar pattern for GitLab API |
