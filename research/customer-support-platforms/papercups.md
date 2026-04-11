---
title: Papercups
slug: papercups
resource_url: https://github.com/papercups-io/papercups
type: customer-support-platform
status: active
last_reviewed: 2026-04-11
next_review: 2026-07-11
---

# Papercups

## Overview

Papercups is an open-source customer support platform written in Elixir that provides self-hosted customer messaging and support ticketing. The project offers both a self-hosted deployment option and a managed hosting service at app.papercups.io. It is actively maintained but announced as being in maintenance mode, meaning no major new features are planned while bug fixes and pull requests are still accepted.

**Key Identity**:
- **Language**: Elixir (backend), TypeScript/React (frontend)
- **License**: MIT
- **Latest Update**: 2022-05-10 (last commit in shallow clone)
- **Repository**: <https://github.com/papercups-io/papercups>
- **Status**: Maintenance mode (announced in README)

## Problem Addressed

Papercups addresses the need for privacy-conscious organizations to maintain customer communications without sending data to third-party SaaS providers. The project's README states: "We wanted to make a self-hosted customer support tool like Zendesk and Intercom for companies that have privacy and security concerns about having customer data going to third party services."

The platform consolidates customer conversations from multiple channels (email, SMS, Slack, Mattermost, web chat) into a single unified dashboard where support teams can manage conversations, assign tickets, and track conversations.

## Key Statistics

- **Project Status**: In maintenance mode (as of most recent CHANGELOG entry, July 2021)
- **Elixir Version Required**: ~> 1.10
- **Last Major Activity**: July 2021 (Functions feature launch, @ mentions, canned responses)
- **License**: MIT (Copyright 2020)
- **Architecture**: OTP application with Phoenix web framework, PostgreSQL backend, React frontend

## Key Features

### Communication Channels

Papercups supports multi-channel customer communication and integrations:

1. **Email Integration** - "Reply from email" - use Papercups to answer support tickets via email. Integrates with Gmail API for message synchronization.

2. **SMS Integration** - "Reply from SMS" - forward Twilio conversations and respond to SMS requests from Papercups.

3. **Slack Integration** - connect with Slack to view and reply to messages directly from a Slack channel. Customers can be assigned to conversations and sent files directly from Slack.

4. **Mattermost Integration** - view and reply to messages directly from Mattermost.

5. **Custom Chat Widget** - a customizable chat widget embedded on websites to chat with customers. Available as React component, HTML snippet, React Native component, and Flutter component.

### Core Platform Capabilities

- **Conversation Management** - close, assign, and prioritize conversations
- **@ Mentions** - notify teammates with @ mentions in the dashboard
- **Canned Responses** - save and reuse common replies (saved replies feature)
- **Conversation Reminders/Nudges** - v1 implementation for reminder system
- **Webhook Integrations** - support for event subscriptions with webhooks (documented in wiki)
- **Markdown and Emoji Support** - use markdown and emoji in messages
- **Team Collaboration** - invite teammates to join accounts
- **Customer Management** - track customer metadata, create and view customer notes
- **GitHub Integration** - associate GitHub issues with customer conversations
- **Browser Replay** - session recording and replay capability (rrweb integration based on dependencies)
- **File Attachments** - support for file uploads and attachments
- **Inboxes per Channel** - separate inbox management for chat, Slack, and email channels
- **Customer Search** - basic search functionality in customers view

### Advanced Features

- **Papercups Functions** (Beta as of July 2021) - available at functions.papercups.io
- **Enhanced Message UI** - improved metadata display in email and Slack

## Technical Architecture

### Backend Structure (Elixir/Phoenix)

The backend is organized as a Phoenix 1.5+ application with multiple bounded contexts:

**Core Modules (75+ contexts in lib/chat_api/)**:
- `accounts` - user account management
- `api_keys` - API authentication
- `auth` - authentication and authorization
- `aws` - AWS service integration (S3, Lambda, SES)
- `conversations` - conversation state management
- `customers` - customer data and metadata
- `companies` - organization/company management
- `browser_sessions` - browser replay sessions
- `browser_replay_events` - session event tracking
- `canned_responses` - saved reply templates
- `billing` - Stripe billing integration

**Key Dependencies** (extracted from mix.exs):
- **Phoenix 1.5.5** - web framework with router and view system
- **Phoenix Ecto 4.1** - database abstraction with Ecto ORM
- **Phoenix Pubsub Redis 3.0.0** - real-time updates via Redis pub/sub
- **Oban 2.1.0** - job processing and background tasks
- **Joken 2.0** - JWT token generation and verification
- **Stripity Stripe 2.0** - Stripe payment processing
- **Tesla 1.3 + Hackney 1.17** - HTTP client for external APIs
- **Swoosh 1.0 + Gen SMTP 0.13** - email delivery
- **Google API Gmail 0.13** - Gmail integration
- **OAuth2 0.9** - OAuth authentication
- **Sentry 8.0.0** - error tracking and observability
- **Pow 1.0.18** - user authentication and authorization framework
- **Phoenix Swagger 0.8** - API documentation
- **Appsignal Phoenix 2.0.0** - application performance monitoring
- **Postgrex** - PostgreSQL database driver
- **Scrivener Ecto 2.0** - pagination support

**Data Models and Schemas**:
- Ecto-based ORM with PostgreSQL for persistence
- Schema definitions for conversations, customers, companies, accounts, messages, and integrations

**Real-time Communication**:
- Phoenix PubSub with Redis backing for multi-instance deployments
- WebSocket channels for live updates

### Frontend Structure (TypeScript/React)

The React UI application (in assets/) uses TypeScript and includes:

**Key Frontend Dependencies**:
- **React 16.13.1** - component framework
- **React Router DOM 5.2.0** - client-side routing
- **Ant Design 4.3.5** - UI component library
- **React Helmet 6.1.0** - document head management
- **Theme UI 0.3.1** - design system and theming
- **Recharts 1.8.5** - charting and visualization
- **React Markdown 4.3.1** - markdown rendering
- **React Syntax Highlighter 12.2.1** - code highlighting
- **Monaco Editor 4.2.1** - code editing widget
- **Stripe React 1.1.2** - payment form UI
- **rRweb 0.9.7** - session recording library
- **LogRocket 1.0.10** - user session replay
- **Sentry React 5.20.1** - error tracking
- **PostHog 1.4.4** - product analytics

**Architecture**:
- Built with Create React App (react-scripts 3.4.1)
- TypeScript for type safety (~3.9.7)
- Ant Design for UI components and styled layout
- Redux-style state management patterns (based on dependencies)
- Build output goes to priv/static/ via cpx copy utility

### Deployment

**Supported Deployment Methods**:
1. **Heroku (One-Click Deploy)** - automated deployment button with buildpacks for Elixir and Phoenix static assets
2. **Docker** - Dockerfile included for containerization
3. **Self-hosted** - manual deployment to any Elixir-capable host
4. **Managed Hosting** - app.papercups.io provides hosted version

**Database**: PostgreSQL (configured in Heroku env)

### Integration Points

**External Services**:
- Stripe (payment processing)
- Twilio (SMS)
- Gmail API (email)
- Slack API (messaging)
- AWS (S3 for files, Lambda, SES for email)
- Sentry (error tracking)
- Mailgun (email delivery option)
- Google Analytics

**Extension Mechanism**:
- Webhook system for event subscriptions (documented in wiki)
- OAuth2 integration pattern for third-party services
- Custom field support for storing additional metadata

## Installation & Usage

### Development Setup

Per CONTRIBUTING.md, development setup is documented in the wiki: <https://github.com/papercups-io/papercups/wiki/Development-Setup>

**Quick Start for Self-Hosting**:

1. One-click Heroku deployment available via app.json configuration
2. Environment variables required (from .env.example):
   - `SECRET_KEY_BASE` - signing key
   - `BACKEND_URL` - backend deployment URL
   - `REACT_APP_URL` - frontend URL
   - Slack credentials (optional): `PAPERCUPS_SLACK_CLIENT_ID`, `PAPERCUPS_SLACK_CLIENT_SECRET`
   - Email configuration: `FROM_ADDRESS`, `MAILGUN_API_KEY`, `DOMAIN`
   - Optional: Stripe keys, Sentry DSN, Google Analytics ID

**Build Commands** (from package.json):
- `npm run build` - production build
- `npm start` - development server
- `npm run prettier` - code formatting
- `npm test` - run tests

**Mix Commands** (Elixir):
- `mix setup` - install deps and setup database
- `mix test` - run test suite
- `mix ecto.migrate` - apply database migrations

### Chat Widget Integration

The chat widget is available as a separate project at <https://github.com/papercups-io/chat-widget>

**Supported Integration Methods**:
- React component import
- Plain HTML snippet
- React Native (github.com/papercups-io/chat-widget-native)
- Flutter (github.com/papercups-io/papercups_flutter)

## Limitations and Caveats

### Project Maturity

The README prominently states: "Papercups is in maintenance mode. This means there won't be any major new features in the near future. We will still accept pull requests and conduct major bug fixes."

This indicates the project is stable for production use but should not be chosen for organizations expecting ongoing feature development.

### Technology Stack Considerations

1. **Elixir Requirement** - Deploying requires Elixir/OTP infrastructure; not suitable for Node.js-only environments
2. **PostgreSQL Requirement** - Hard dependency on PostgreSQL; no support for other databases
3. **Front-end Update Lag** - React version 16.13.1 is outdated (as of 2026); no active updates indicated
4. **Dependency Version Freeze** - Dependencies locked in 2020-2021 timeframe; potential security concerns if not actively monitored

### Operational Considerations

1. **Redis Dependency for Scale** - Phoenix Pubsub Redis required for multi-instance deployments
2. **Email Configuration Required** - Mailgun or SES configuration needed for email features
3. **Stripe Integration** - Payment processing tied to Stripe
4. **Hosted Pricing** - Managed app.papercups.io service not free; self-hosting requires infrastructure

### Feature Gaps (as of last documentation)

- Not mentioned in documentation: automated response routing, AI-powered suggestions, sentiment analysis, advanced reporting/analytics

## Relevance to Claude Code Development

Papercups is relevant to Claude Code development as a reference for:

1. **Multi-Channel Integration Pattern** - demonstrates consolidating communication from email, SMS, Slack, web chat into unified platform; applicable for agents managing conversations across multiple channels

2. **Real-time Architecture** - Phoenix Pubsub with Redis provides pattern for real-time updates in distributed agent systems

3. **Context Management** - bounded context architecture (75+ contexts in chat_api) shows approach to organizing business logic in complex domain (conversations, customers, integrations)

4. **Integration Extensibility** - webhook system and OAuth2 patterns show how to enable third-party integrations; useful for agent skill composition

5. **Deployment Strategy** - multi-deployment-option approach (Heroku, Docker, self-hosted) relevant for agent infrastructure deployment

6. **TypeScript/React Frontend** - browser-based chat UI patterns could inform agent UI components for customer-facing chat widgets

Papercups is NOT directly used by Claude Code but serves as an architectural reference for building multi-channel, real-time collaborative systems.

## References

- **README**: <https://github.com/papercups-io/papercups/blob/master/README.md> (accessed 2026-04-11)
- **Contributing Guide**: <https://github.com/papercups-io/papercups/blob/master/CONTRIBUTING.md> (accessed 2026-04-11)
- **CHANGELOG**: <https://github.com/papercups-io/papercups/blob/master/CHANGELOG.md> (accessed 2026-04-11)
- **Development Setup Wiki**: <https://github.com/papercups-io/papercups/wiki/Development-Setup> (referenced in CONTRIBUTING.md)
- **Event Subscriptions/Webhooks**: <https://github.com/papercups-io/papercups/wiki/Event-Subscriptions-with-Webhooks> (referenced in CHANGELOG)
- **mix.exs** - Project dependencies (accessed 2026-04-11)
- **assets/package.json** - Frontend dependencies (accessed 2026-04-11)
- **app.json** - Heroku deployment configuration (accessed 2026-04-11)
- **LICENSE** - MIT License, Copyright 2020 (accessed 2026-04-11)

## Freshness Tracking

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | README extracted directly; status verified from maintenance notice |
| Problem Addressed | high | Direct quote from README philosophy section |
| Key Statistics | high | From mix.exs, package.json, CHANGELOG; commit date from git history |
| Key Features | high | Extracted from README features list and CHANGELOG 2021 updates |
| Technical Architecture | high | Direct from mix.exs dependencies, lib/ directory structure, and assets/package.json |
| Installation & Usage | medium | Development setup documented in wiki; quick start inferred from app.json and .env.example |
| Limitations | medium | Maintenance mode status from README; technology stack considerations from dependency analysis; feature gaps inferred from absence in docs |
| Relevance | medium | Architectural analysis based on code structure; not empirically tested for agent integration |

**Review Schedule**: Review next on 2026-07-11 to check for maintenance updates, security patches, or project status changes.
