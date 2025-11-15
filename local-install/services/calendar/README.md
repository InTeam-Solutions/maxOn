# Calendar Feed MVP

Async FastAPI service that stores calendars/events in PostgreSQL and exposes a read-only iCal feed compatible with Apple Calendar, Google Calendar, and any client that understands `.ics` subscriptions.

## Stack
- Python 3.11, FastAPI, uvicorn
- SQLAlchemy 2.x (async) + PostgreSQL
- icalendar for `.ics` generation
- Poetry for dependency management
- Docker + docker-compose

## Quick start

The API listens on `http://localhost:7133`. Swagger UI stays available at `http://localhost:7133/docs`.

### Environment
Сервис читает переменные с префиксом `CALENDAR_` (например, `CALENDAR_DATABASE_URL`). В docker-compose они прокидываются из корневого `.env`, так что дополнительных настроек не требуется.

## REST API workflow

### 1. Create a calendar
```bash
curl -X POST http://localhost:7133/api/calendars \
  -H "Content-Type: application/json" \
  -d '{
        "user_id": 12345678,
        "name": "Product Launch"
      }'
```
Response contains the calendar UUID, `user_id`, and the public `.ics` URL. Save the URL – оно же используется в клиентах.

Если нужно гарантированно получить календарь по пользователю (создать, если его ещё нет), вызывайте:
```bash
curl -X POST http://localhost:7133/api/calendars/users/<user_id>/calendar
```
А чтобы просто прочитать – `GET http://localhost:7133/api/calendars/users/<user_id>/calendar`.

### 2. Create an event
```bash
curl -X POST http://localhost:7133/api/calendars/<calendar_id>/events \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Dry run",
        "brief_description": "Full rehearsal",
        "start_datetime": "2025-11-10T10:00:00Z",
        "duration_minutes": 60
      }'
```
Each event is stored as CONFIRMED; there is no update/delete in this MVP.

### 3. (Optional) Inspect data
- `GET /api/calendars/<calendar_id>` – calendar info plus events
- `GET /api/calendars/<calendar_id>/events` – events only

### 4. Fetch the `.ics` feed
```
https://localhost:7133/calendar/<public_token>.ics
```
The token comes from the `public_ics_url` returned when the calendar was created.

## Subscribing in calendar clients
1. **Google Calendar** → left sidebar `Other calendars` → `From URL` → paste the `.ics` link → `Add calendar`.
2. **Apple Calendar (macOS)** → `File` → `New Calendar Subscription…` → paste the `.ics` link → adjust refresh interval if needed.

Clients will poll the feed periodically; every new event you POST appears automatically.

## Tests
```bash
pytest
```
Tests cover calendar creation, event creation, and verifying that the `.ics` feed includes CONFIRMED events.
