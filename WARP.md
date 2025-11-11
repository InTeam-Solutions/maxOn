# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Quick commands

Prerequisites: Docker + Docker Compose. Create a root .env with required keys: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, POSTGRES_PASSWORD (optionally POSTGRES_USER, POSTGRES_DB, LOG_LEVEL).

- Start all services (build if needed)
  ```bash
  docker compose up -d
  ```
- Stop all services
  ```bash
  docker compose down
  ```
- Status and logs
  ```bash
  docker compose ps
  docker compose logs -f            # all
  docker compose logs -f core       # single service
  ```
- Rebuild a service after code changes
  ```bash
  docker compose build core && docker compose up -d core
  # replace `core` with: context | llm | orchestrator | api-gateway
  ```
- Recreate from scratch (destroys volumes)
  ```bash
  docker compose down -v && docker compose up -d
  ```
- Health and docs endpoints (when running)
  ```bash
  curl http://localhost:8004/health  # core
  curl http://localhost:8002/health  # context
  curl http://localhost:8003/health  # llm
  # Swagger UI:
  # Core:     http://localhost:8004/docs
  # Context:  http://localhost:8002/docs
  # LLM:      http://localhost:8003/docs
  ```

Testing
- There is no automated test suite configured. Manual API testing examples are in README.md (curl snippets).
- A standalone Mixpanel check exists and can be run individually:
  ```bash
  # Requires MIXPANEL_TOKEN in .env
  python test_mixpanel.py
  ```

## High-level architecture

Microservices with shared utilities and schemas. Primary flow: Telegram (API Gateway) → Orchestrator → LLM/Context/Core. Data persisted in Postgres; hot context and caches in Redis. All services are containerized and wired via docker-compose.

- API Gateway (services/api-gateway)
  - Telegram bot (Aiogram v3), UI rendering, routes user interactions to Orchestrator.
- Orchestrator (services/orchestrator)
  - Coordinates multi-step dialogs and intent execution; routes to LLM, Context, and Core.
- LLM Service (services/llm)
  - OpenAI client; Jinja2-templated prompts for intent parsing, summarization, and goal step generation.
- Context Service (services/context)
  - Builds per-user LLM context; stores conversation history and session state (Redis + Postgres).
- Core Service (services/core)
  - Business domain (Events, Goals/Steps, Products, Cart) on FastAPI + SQLAlchemy; owns database schema.
- Shared (shared/)
  - Pydantic schemas and common utilities (logger, HTTP client, analytics, pricing); database helpers in shared/database.py.

Ports (host):
- Orchestrator 8001, Context 8002, LLM 8003, Core 8004. Postgres 5432, Redis 6379.

Notes:
- docker-compose defines: postgres, redis, core, context, llm, orchestrator, api-gateway. RabbitMQ and worker are referenced in docs but not active in the current compose file.
- Legacy monolith at mvp/ is not used by docker-compose; the active implementation is under services/.

## Development notes (from CLAUDE.md, adapted)

- Changing domain models (e.g., Event fields)
  - Update SQLAlchemy model in services/core/app/models/*.py
  - Update Pydantic schemas in shared/schemas/*.py
  - If surfaced in responses/UI, adjust API handlers and api-gateway renderer as needed
  - Rebuild and restart the affected service(s)

- Adding a new intent
  - Define intent format and examples in services/llm/app/prompts/system.py
  - Update intent routing/handlers in services/orchestrator/app/main.py (and state machine if required)
  - Adjust services/llm/app/prompts/summarizer.py if response strategy changes
  - Add/modify Core endpoints if the intent needs new server-side operations

- Context building changes
  - Modify services/context/app/services/context_builder.py (and related models/schemas)
  - Ensure prompt templates in services/llm/app/prompts/ consume any new context fields

- Prompt files
  - system.py: main system prompt and intent schemas
  - summarizer.py: final text vs table rendering vs clarification
  - goal_coach.py: generation of actionable micro-steps for goals

## Cross-references

- README.md: quick start, service endpoints, manual API testing, and common docker-compose commands.
- CLAUDE.md: deeper architectural details, file pointers, and modification guidelines. If .env is tracked, follow its guidance to remove it from version control.
