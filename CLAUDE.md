# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot-based productivity assistant with LLM-powered natural language processing. The bot helps users manage events, track goals with auto-generated steps, and stay motivated through conversational commands in Russian. It uses OpenAI's GPT-4o to parse user messages into structured intents, performs database operations, and generates motivating responses.

**NOTE:** The repository contains two implementations:
- `/mvp/` - Legacy monolithic implementation (not actively used)
- `/services/` - **Active microservices architecture** (used by docker-compose.yml)

All file paths below reference the `/services/` directory unless otherwise specified.

## Architecture

### Microservices Architecture

1. **API Gateway** (`services/api-gateway/`)
   - Telegram bot using Aiogram v3 (`app/main.py`: 1002 lines)
   - Rich HTML rendering with inline keyboards (`app/renderer.py`)
   - Dashboard UI with event calendar and goal progress
   - Routes all processing to Orchestrator service

2. **Orchestrator** (`services/orchestrator/`)
   - Coordinates between Context, LLM, and Core services (`app/main.py`: 679 lines)
   - Dialog state machine for multi-turn conversations (`app/state_machine.py`)
   - Handles intent execution and response summarization
   - Manages conversation flow and clarification requests

3. **LLM Service** (`services/llm/`)
   - Parses natural language → structured JSON intents
   - Generates goal steps based on user's level and time commitment
   - Summarizes results into user-facing responses
   - Uses OpenAI GPT-4o (via proxy: `https://api.proxyapi.ru/openai/v1`)
   - Jinja2-templated prompts with dynamic context injection

4. **Core Service** (`services/core/`)
   - Database operations for events, goals, steps, products, cart (`app/main.py`: 523 lines)
   - PostgreSQL with SQLAlchemy ORM
   - User-scoped data with multi-tenancy support
   - Separate service modules for each domain (`app/services/`)

5. **Context Service** (`services/context/`)
   - Builds rich LLM context from user data (`app/services/context_builder.py`)
   - Manages conversation history and session state
   - Tracks active goals and upcoming events for context injection
   - Redis + PostgreSQL storage for fast access
   - User profiles with timezone support

6. **Shared Utilities** (`shared/`)
   - Database initialization and session management (`database.py`)
   - Pydantic schemas for all entities (`schemas/`)
   - Mixpanel analytics integration (`utils/analytics.py`)
   - Logging, HTTP clients, pricing utilities

### Intent System

Supported intents (defined in `services/llm/app/prompts/system.py`):
- **small_talk**: Motivating conversational responses
- **event.search**: Find events by filters (title, date range, time)
- **event.mutate**: Create/update/delete events
- **goal.search**: Show all user goals with progress
- **goal.create**: Create goal with auto-generated steps (LLM generates steps based on user level & time)
- **goal.delete**: Delete a goal
- **goal.query**: Show progress for specific goal
- **goal.update_step**: Mark step as pending/in_progress/completed
- **goal.add_step**: Add new step to existing goal
- **goal.delete_step**: Delete step from goal
- **product.search**: Find products for goals (future feature)

### UI/UX Design (`services/api-gateway/app/renderer.py`)

Rich Telegram HTML formatting with:

**Events:**
- 📅 Event title with emoji header
- Formatted dates: "Пн, 01.10.2025"
- Bold time display
- Repeat indicators (🔁)
- Notes in italics with 💬 icon

**Goals:**
- 🎯 Goal title with status emoji (✅/🎯/📦)
- Progress bar: █████░░░░░ 50%
- Description with 💡 icon (truncated if > 100 chars)
- Step counter: "Шагов: 2/6"
- First 3 steps shown with status:
  - ✅ Completed
  - 🔄 In progress
  - ⭕ Pending
- "...и еще N" for remaining steps

### Result Set Reference System

Search results are stored with UUID `set_id` to enable follow-up operations:
- User: "Show meetings tomorrow" → Returns set_id with results
- User: "Delete the second one" → References set_id + ordinal=2
- Enables multi-turn conversations without re-parsing natural language

## Development Commands

### Running the Bot

All services run via Docker Compose:

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f api-gateway
docker compose logs -f orchestrator
docker compose logs -f llm

# Rebuild specific service after code changes
docker compose build orchestrator
docker compose up -d orchestrator

# Stop all services
docker compose down
```

### Services and Ports

- **API Gateway (Telegram Bot)**: Internal only, connects to Telegram API
- **Orchestrator**: `http://localhost:8001`
- **Context Service**: `http://localhost:8002`
- **LLM Service**: `http://localhost:8003`
- **Core Service**: `http://localhost:8004`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
  - Database 0: Core Service cache
  - Database 1: Context Service cache
  - Database 2: LLM Service cache
  - Database 3: Orchestrator cache

### Database Setup

PostgreSQL runs in Docker. Connection string in `.env`:
```
DATABASE_URL=postgresql+psycopg2://user:password@postgres:5432/initio_db
```

Schema is auto-created by Core Service on first run via Alembic migrations.

### Environment Variables

Required in root `.env`:
- `TELEGRAM_BOT_TOKEN`: Telegram bot API token from @BotFather
- `OPENAI_API_KEY`: OpenAI API key for GPT-4o-mini
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string (default: redis://redis:6379)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials

## Key Technical Details

### User ID Management
- Uses Telegram `user_id` as the user identifier throughout the system
- All database queries are scoped by `user_id` to ensure multi-user support
- Passed from Telegram message handler (`message.from_user.id`) down to core functions

### Date/Time Handling
- All dates in format: `YYYY-MM-DD`
- All times in format: `HH:MM` (seconds/microseconds stripped)
- LLM prompts include current datetime in user's timezone via `NOW=` injection
- Uses `python-dateutil` for flexible parsing

### Database Session Management
- Lazy singleton pattern: `init_db()` called once at startup
- Context manager pattern: `with db.session_ctx() as s:` auto-commits/rollbacks
- Uses SQLAlchemy future-style API

### Error Handling
- LLM parsing errors bubble up but are caught in app.py message handler
- Core returns structured error responses with `error=True` flag
- User sees generic "Упс, произошла ошибка" message on exceptions

## LLM Prompt Design

Prompts are Jinja2 templates in `services/llm/app/prompts/`:

### `system.py` - Main System Prompt
- Defines all 11 intent JSON formats with examples
- Forces LLM to convert relative dates ("завтра", "на следующей неделе") to YYYY-MM-DD
- Prevents LLM from inventing event IDs
- Instructs on dry_run usage for previews
- **Dynamic context injection via Jinja2:**
  - `{{ user_name }}` - User's first name
  - `{{ timezone }}` - User's timezone (e.g., "Europe/Moscow")
  - `{{ now }}` - Current datetime formatted as "NOW=2025-10-15 14:30"
  - `{{ active_goals }}` - List of user's active goals with progress
  - `{{ upcoming_events }}` - Events for next 7 days
  - `{{ conversation_history }}` - Last 5 messages for context
  - `{{ state_context }}` - Dialog state machine context (if mid-flow)

### `summarizer.py` - Response Summarization
- Defines three response strategies:
  - `final_text`: Simple text response
  - `render_table`: Triggers event/goal list rendering with set_id
  - `ask_clarification`: Requests more info from user
- Uses same context injection as system prompt

### `goal_coach.py` - Goal Step Generation
- Generates actionable micro-steps for user goals
- Takes into account: user's skill level, available time, goal complexity
- Returns structured JSON with steps in priority order

## Code Modification Guidelines

### When Adding New Event Fields
1. Update `Event` model in `services/core/app/models/event.py`
2. Add field to Pydantic schemas in `shared/schemas/events.py`
3. Update CRUD operations in `services/core/app/services/events.py` to handle the new field
4. Modify LLM prompts in `services/llm/app/prompts/system.py` to extract/format the field
5. Update renderer if field should display: `services/api-gateway/app/renderer.py`

### When Adding New Intents
1. Define intent format in `services/llm/app/prompts/system.py` (add to supported intents list)
2. Add handler in `services/orchestrator/app/main.py` (update intent routing logic)
3. Update `services/llm/app/prompts/summarizer.py` if new response strategy needed
4. Add corresponding API endpoint in Core Service if needed

### When Adding New Goal/Step Logic
1. Update models in `services/core/app/models/goal.py` (Goal or Step SQLAlchemy models)
2. Update schemas in `shared/schemas/goals.py` (Pydantic models)
3. Update business logic in `services/core/app/services/goals.py`
4. If LLM should generate steps differently, modify `services/llm/app/prompts/goal_coach.py`

### When Changing Date/Time Formats
- Update parsing logic in `services/core/app/services/events.py`
- Update format examples in `services/llm/app/prompts/system.py`
- Update serialization in model's `to_dict()` method in `services/core/app/models/event.py`

### When Modifying Context Building
- Update context construction in `services/context/app/services/context_builder.py`
- Ensure Jinja2 templates in `services/llm/app/prompts/` use new context variables
- Update context schemas in `shared/schemas/context.py` if structure changes

## Key File Locations Reference

### Models (SQLAlchemy)
- Events: `services/core/app/models/event.py`
- Goals & Steps: `services/core/app/models/goal.py`
- Products & Cart: `services/core/app/models/product.py`
- User Profiles: `services/context/app/models/user.py`
- Conversations: `services/context/app/models/conversation.py`
- Sessions: `services/context/app/models/session.py`

### Schemas (Pydantic)
- All schemas: `shared/schemas/` (events.py, goals.py, products.py, context.py)

### Business Logic
- Event CRUD: `services/core/app/services/events.py`
- Goal/Step management: `services/core/app/services/goals.py`
- Product operations: `services/core/app/services/products.py`
- Context building: `services/context/app/services/context_builder.py`

### LLM Components
- System prompt: `services/llm/app/prompts/system.py`
- Summarizer: `services/llm/app/prompts/summarizer.py`
- Goal coach: `services/llm/app/prompts/goal_coach.py`
- Main LLM API: `services/llm/app/main.py`

### Orchestration & API
- Orchestrator: `services/orchestrator/app/main.py`
- State machine: `services/orchestrator/app/state_machine.py`
- Telegram bot: `services/api-gateway/app/main.py`
- HTML renderer: `services/api-gateway/app/renderer.py`

### Shared Utilities
- Database setup: `shared/database.py`
- Analytics (Mixpanel): `shared/utils/analytics.py`
- Logger: `shared/utils/logger.py`

## Analytics Integration

The system tracks user actions via Mixpanel (`shared/utils/analytics.py`):

**Events tracked:**
- Bot Started (user_id, timestamp)
- Intent Parsed (intent_type, confidence)
- Goal Created/Updated/Deleted
- Event Created/Updated/Deleted
- Step Completed

**User properties set:**
- Name, timezone, language
- Total goals, completed goals
- Total events
- Last active timestamp

## Security Notes

**IMPORTANT**: The `.env` file contains sensitive credentials and is currently tracked in git. This should be removed from version control:
```bash
git rm --cached .env
echo ".env" >> .gitignore
```