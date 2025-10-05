# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot-based productivity assistant with LLM-powered natural language processing. The bot helps users manage events, track goals with auto-generated steps, and stay motivated through conversational commands in Russian. It uses OpenAI's GPT-4 to parse user messages into structured intents, performs database operations, and generates motivating responses.

## Architecture

### Microservices Architecture

1. **API Gateway** (`services/api-gateway/`)
   - Telegram bot interface using Aiogram
   - Renders responses in rich HTML format with emojis and progress bars
   - Routes all processing to Orchestrator service

2. **Orchestrator** (`services/orchestrator/`)
   - Coordinates between Context, LLM, and Core services
   - Implements business logic for goals (auto-generation of steps via LLM)
   - Handles intent execution and response summarization

3. **LLM Service** (`services/llm/`)
   - Parses natural language → structured JSON intents
   - Generates goal steps based on user's level and time commitment
   - Summarizes results into user-facing responses
   - Uses OpenAI GPT-4o-mini with proactive coaching prompts

4. **Core Service** (`services/core/`)
   - Database operations for events, goals, steps, products
   - PostgreSQL with SQLAlchemy ORM
   - User-scoped data with multi-tenancy support

5. **Context Service** (`services/context/`)
   - Manages conversation history and session state
   - Tracks active goals and upcoming events for context injection
   - Redis-backed storage for fast access

### Intent System

Supported intents:
- **small_talk**: Motivating conversational responses
- **event.search**: Find events by filters (title, date range, time)
- **event.mutate**: Create/update/delete events
- **goal.search**: Show all user goals with progress
- **goal.create**: Create goal with auto-generated steps
- **goal.delete**: Delete a goal
- **goal.query**: Show progress for specific goal
- **goal.update_step**: Mark step as pending/in_progress/completed
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

System prompts live in `mvp/llm/prompts.py`:

- **SYSTEM_PROMPT**: Defines intent JSON formats and date parsing rules
  - Forces LLM to convert relative dates ("завтра", "на следующей неделе") to YYYY-MM-DD
  - Prevents LLM from inventing event IDs
  - Instructs on dry_run usage for previews

- **SUMMARIZE_PROMPT**: Defines three response strategies
  - `final_text`: Simple text response
  - `render_table`: Triggers event list rendering with set_id
  - `ask_clarification`: Requests more info from user

## Code Modification Guidelines

### When Adding New Event Fields
1. Update `Event` model in `core/models.py`
2. Add field to `EventPatch` dataclass in `core/selectors.py`
3. Update `mutate_events()` in `core/events.py` to handle the new field
4. Modify LLM prompts in `llm/prompts.py` to extract/format the field

### When Adding New Intents
1. Define intent format in `SYSTEM_PROMPT` (`llm/prompts.py`)
2. Add handler in `handle_intent()` (`core/router.py`)
3. Update `SUMMARIZE_PROMPT` if new response strategy needed

### When Changing Date/Time Formats
- Update parsing logic in `core/events.py`: `_parse_date()`, `_parse_time()`
- Update format examples in `SYSTEM_PROMPT`
- Update `to_dict()` serialization in `core/models.py`

## Security Notes

**IMPORTANT**: The `.env` file contains sensitive credentials and is currently tracked in git. This should be removed from version control:
```bash
git rm --cached mvp/.env
echo "mvp/.env" >> .gitignore
```