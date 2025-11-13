# Контекст проекта maxOn для AI-агента

## 🎯 О проекте

**maxOn** — это AI-коуч и планировщик намерений для национального мессенджера MAX. Telegram-бот с микросервисной архитектурой, который помогает пользователям достигать целей через умную декомпозицию, SMART-анализ и систему напоминаний.

## 🏗️ Архитектура проекта

### Технологический стек
- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **Bot Framework**: Aiogram 3.13.1 (Telegram)
- **AI**: OpenAI GPT-4o через ProxyAPI
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Task Scheduler**: APScheduler 3.10.4
- **Deployment**: Docker Compose

### Микросервисная архитектура

```
┌─────────────────┐
│  Telegram Bot   │  ← Пользователь взаимодействует здесь
│  (API Gateway)  │
└────────┬────────┘
         │
    ┌────▼─────────┐
    │ Orchestrator │  ← Координирует запросы между сервисами
    └─┬──┬────┬────┘
      │  │    │
  ┌───▼──▼────▼───┐
  │ Context │ LLM │ Core │ Worker │  ← Специализированные сервисы
  └─────────┴─────┴──────┴────────┘
          │
    ┌─────▼──────┐
    │ PostgreSQL │  ← Единая база данных
    │   Redis    │  ← Кеш и сессии
    └────────────┘
```

### 6 основных сервисов:

1. **API Gateway** (Telegram Bot) - `/services/api-gateway/`
   - Обрабатывает сообщения от пользователей
   - Rich HTML рендеринг с InlineKeyboards
   - Команды: `/start`, `/goals`, `/events`, `/settings`
   - Управление состояниями (editing, goal_clarification, etc.)
   - Файл: `app/main.py` (3700+ строк)

2. **Orchestrator** (:8001) - `/services/orchestrator/`
   - Координирует работу между сервисами
   - State Machine для многошаговых диалогов
   - Обрабатывает SMART-анализ целей
   - Планирует шаги в календаре
   - Файл: `app/main.py` (679 строк)

3. **Core Service** (:8004) - `/services/core/`
   - CRUD операции для всех сущностей
   - Модели: Event, Goal, Step, Product, CartItem, User
   - REST API с Swagger документацией
   - Файл: `app/main.py` (734 строки)

4. **Context Service** (:8002) - `/services/context/`
   - Управление историей диалогов
   - Профили пользователей с timezone
   - Сессии и состояния
   - Построение контекста для LLM

5. **LLM Service** (:8003) - `/services/llm/`
   - Интеграция с OpenAI GPT-4o
   - Парсинг natural language → structured JSON
   - Jinja2 промпты с контекстом
   - SMART-анализ целей
   - Генерация шагов (goal_coach)

6. **Worker Service** (:8005) - `/services/worker/` ⭐ NEW
   - APScheduler для фоновых задач
   - 4 типа уведомлений:
     - Event reminders (каждую минуту)
     - Goal deadline warnings (ежедневно 9:00)
     - Unfinished step reminders (ежедневно 20:00)
     - Motivational messages (ежедневно 8:00)
   - Прямая отправка через Telegram Bot API

## 📊 Структура базы данных

### Core Service Tables:

```sql
-- Пользователи (NEW)
users (
  user_id VARCHAR(64) PRIMARY KEY,
  chat_id VARCHAR(64) NOT NULL,
  timezone VARCHAR(64) DEFAULT 'Europe/Moscow',
  notification_enabled BOOLEAN DEFAULT TRUE,
  event_reminders_enabled BOOLEAN DEFAULT TRUE,
  goal_deadline_warnings_enabled BOOLEAN DEFAULT TRUE,
  step_reminders_enabled BOOLEAN DEFAULT TRUE,
  motivational_messages_enabled BOOLEAN DEFAULT TRUE
)

-- События с напоминаниями
events (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(64),
  title VARCHAR(255),
  date DATE,
  time TIME,
  duration_minutes INT,
  repeat VARCHAR(64),
  notes TEXT,
  event_type VARCHAR(32) DEFAULT 'user',
  linked_step_id INT,
  linked_goal_id INT,
  reminder_minutes_before INT DEFAULT 15,  -- NEW
  reminder_enabled BOOLEAN DEFAULT TRUE     -- NEW
)

-- Цели
goals (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(64),
  title VARCHAR(255),
  description TEXT,
  status VARCHAR(32) DEFAULT 'active',
  progress_percent FLOAT DEFAULT 0,
  target_date DATE,
  target_deadline DATE,
  is_scheduled BOOLEAN DEFAULT FALSE
)

-- Шаги целей
steps (
  id SERIAL PRIMARY KEY,
  goal_id INT REFERENCES goals(id),
  title VARCHAR(255),
  order INT,
  status VARCHAR(32) DEFAULT 'pending',
  estimated_hours FLOAT,
  completed_at TIMESTAMP,
  planned_date DATE,
  planned_time TIME,
  duration_minutes INT,
  linked_event_id INT
)
```

### Context Service Tables:
- `user_profiles` - расширенные профили
- `conversation_messages` - история сообщений
- `session_states` - текущие состояния диалога

## 🔑 Ключевые особенности кодовой базы

### 1. Intent System (LLM Service)

Поддерживаемые интенты в `services/llm/app/prompts/system.py`:
- `small_talk` - обычный разговор
- `event.search` - поиск событий
- `event.mutate` - создание/изменение/удаление событий
- `goal.search` - показать все цели
- `goal.create` - создать цель с шагами
- `goal.delete` - удалить цель
- `goal.query` - показать прогресс конкретной цели
- `goal.update_step` - обновить статус шага
- `goal.add_step` - добавить новый шаг
- `goal.delete_step` - удалить шаг
- `product.search` - поиск товаров (будущее)

### 2. State Machine (Orchestrator)

Состояния диалога:
```python
class DialogState(str, Enum):
    IDLE = "idle"
    GOAL_CLARIFICATION = "goal_clarification"
    GOAL_EDITING = "goal_editing"
    EVENT_EDIT_* = "event_edit_title", "event_edit_date", etc.
    GOAL_EDIT_* = "goal_edit_title", "goal_edit_deadline", etc.
    STEP_EDIT_* = "step_edit_title", etc.
```

### 3. Telegram UI Patterns (API Gateway)

**Главное меню:**
```python
[🎯 Мои цели] [📅 Календарь]
[➕ Новая цель] [➕ Событие]
```

**Управление целями:**
```python
🎯 [Название цели] ✅ 75%
▶ [Посмотреть детали]
▶ [Удалить цель]
```

**Календарь (grouped by date):**
```markdown
━━━ Понедельник, 11.11 ━━━
⏰ 15:00  Встреча с клиентом (2ч)

━━━ Вторник, 12.11 ━━━
⏰ 10:00  Созвон команды (1ч)
```

### 4. SMART Goal Analysis Flow

1. Пользователь отправляет цель
2. LLM анализирует по SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
3. Orchestrator предлагает улучшения
4. Пользователь подтверждает/редактирует
5. LLM генерирует пошаговый план (goal_coach)
6. Шаги автоматически планируются в календаре

### 5. Notification System (Worker)

**Архитектура:**
- APScheduler с Redis JobStore
- Прямые запросы к PostgreSQL
- Отправка через Aiogram Bot
- Timezone-aware scheduling

**Задачи:**
```python
# Event Reminders (interval: 1 minute)
- Проверяет: event_datetime - reminder_minutes_before ≈ NOW
- Отправляет: Детали события + время до начала

# Goal Deadlines (cron: 9:00)
- Проверяет: target_date in [today + 7d, 3d, 1d, 0d]
- Отправляет: Прогресс + дедлайн + мотивация

# Step Reminders (cron: 20:00)
- Проверяет: status='in_progress' AND planned_date < today
- Отправляет: Список просроченных шагов по целям

# Motivational (cron: 8:00)
- Проверяет: active_goals count > 0
- Отправляет: Случайная мотивация + текущие цели
```

## 🚀 Команды для работы

### Запуск проекта
```bash
cd /Users/asgatakmaev/Desktop/business/maxOn

# Запустить всё
docker compose up -d

# Проверить статусы
docker compose ps

# Логи конкретного сервиса
docker compose logs -f worker
docker compose logs -f api-gateway
docker compose logs -f orchestrator

# Перезапустить после изменений
docker compose build <service>
docker compose up -d <service>
```

### Проверка Worker
```bash
# Список запланированных задач
curl http://localhost:8005/jobs | python3 -m json.tool

# Health check
curl http://localhost:8005/health
```

### Работа с базой данных
```bash
# Подключиться к PostgreSQL
docker compose exec postgres psql -U initio -d initio

# Посмотреть пользователей
SELECT * FROM users;

# События с напоминаниями
SELECT id, title, date, time, reminder_minutes_before, reminder_enabled
FROM events
WHERE reminder_enabled = true;
```

## 🔧 Типичные задачи разработки

### Добавить новое поле в модель

1. **Обновить SQLAlchemy модель** (напр. `services/core/app/models/event.py`)
2. **Обновить Pydantic схемы** (`shared/schemas/events.py`)
3. **Обновить CRUD методы** (`services/core/app/services/events.py`)
4. **Перезапустить Core:** `docker compose restart core`

### Изменить LLM промпты

Файлы промптов (Jinja2):
- `services/llm/app/prompts/system.py` - основной парсинг
- `services/llm/app/prompts/summarizer.py` - форматирование ответов
- `services/llm/app/prompts/goal_coach.py` - генерация шагов

После изменений: `docker compose restart llm`

### Добавить новый тип уведомлений

1. Создать файл `services/worker/app/tasks/new_task.py`
2. Импортировать модели: `from core_models.event import Event`
3. Зарегистрировать в `services/worker/app/scheduler.py`
4. Пересобрать: `docker compose build worker && docker compose up -d worker`

### Добавить команду в бота

В `services/api-gateway/app/main.py`:
```python
@dp.message(Command("newcommand"))
async def cmd_newcommand(message: Message):
    user_id = str(message.from_user.id)
    # ваша логика
```

## 📝 Важные файлы для понимания

### Обязательно изучить:
1. **CLAUDE.md** - полная архитектура и паттерны
2. **docker-compose.yml** - конфигурация всех сервисов
3. **services/api-gateway/app/main.py** - главный файл бота
4. **services/orchestrator/app/main.py** - координация
5. **services/worker/app/scheduler.py** - настройка задач
6. **shared/schemas/** - все Pydantic модели

### Ключевые паттерны:

**Database Session Pattern:**
```python
from shared.database import get_db

db = get_db()
with db.session_ctx() as session:
    # операции с БД
    session.commit()  # auto-commit
```

**HTTP Communication:**
```python
import httpx

http_client = httpx.AsyncClient(timeout=30.0)
response = await http_client.get(f"{CORE_SERVICE_URL}/api/users/{user_id}")
```

**Telegram Message Sending:**
```python
await bot.send_message(
    chat_id=chat_id,
    text=formatted_message,
    parse_mode="HTML",
    reply_markup=keyboard
)
```

## 🐛 Частые проблемы и решения

### Worker не запускается
- **Проблема:** ModuleNotFoundError для core_models
- **Решение:** Проверь Dockerfile, должна быть строка:
  ```dockerfile
  COPY services/core/app/models /app/core_models
  ```

### .env не подтягивается
- **Проблема:** Environment variables not found
- **Решение:** Убедись что `.env` в корне проекта и содержит:
  ```
  TELEGRAM_BOT_TOKEN=...
  OPENAI_API_KEY=...
  POSTGRES_PASSWORD=...
  ```

### Контейнер падает при старте
```bash
# Проверить логи
docker compose logs <service>

# Пересобрать с нуля
docker compose down -v  # ОСТОРОЖНО: удалит данные!
docker compose build --no-cache
docker compose up -d
```

### Уведомления не отправляются
1. Проверь что user создан: `curl http://localhost:8004/api/users/<user_id>`
2. Проверь notification_enabled: должен быть true
3. Проверь chat_id: должен совпадать с Telegram user_id
4. Проверь Worker задачи: `curl http://localhost:8005/jobs`

## 🎯 Цели проекта (Roadmap)

### Реализовано ✅
- Микросервисная архитектура
- Telegram bot с rich UI
- SMART анализ целей
- Автогенерация шагов
- Календарь с группировкой
- Ручное управление через inline buttons
- Система уведомлений (4 типа)
- Настройки пользователя

### В разработке 🚧
- [ ] Product Search - интеграция с маркетплейсами
- [ ] Recurring Events - повторяющиеся события
- [ ] Integration Tests
- [ ] **Адаптация для MAX мессенджера** ⭐
- [ ] Deploy на Kubernetes

## 💡 Подсказки для эффективной работы

1. **Всегда проверяй логи** перед изменениями: `docker compose logs -f`
2. **Используй Swagger UI** для тестирования API: http://localhost:8004/docs
3. **Изучи CLAUDE.md** - там детальное описание всех паттернов
4. **Тестируй локально** перед коммитом: `docker compose up -d`
5. **Не коммить .env** - он в .gitignore
6. **Worker требует пересборки** после изменений в tasks/
7. **Jinja2 промпты** используют двойные фигурные скобки: `{{ variable }}`
8. **Telegram HTML** поддерживает: `<b>`, `<i>`, `<code>`, `<pre>`
9. **User ID** в Telegram = Chat ID для приватных чатов
10. **Redis** используется для: кеша (DB 0-3) и APScheduler JobStore (DB 4)

## 🔐 Секреты и переменные

Файл `.env` уже настроен со следующими переменными:
- `TELEGRAM_BOT_TOKEN` - токен от @BotFather
- `OPENAI_API_KEY` - API ключ OpenAI
- `POSTGRES_PASSWORD` - пароль БД
- `MIXPANEL_TOKEN` - для аналитики

**ВАЖНО:** Никогда не коммить .env в git!

---

## 📞 Следующие шаги

Когда начинаешь работать с проектом:

1. Запусти: `docker compose up -d`
2. Проверь статус: `docker compose ps` (все должны быть "Up")
3. Открой бота в Telegram и отправь `/start`
4. Проверь Worker: `curl http://localhost:8005/jobs`
5. Создай тестовую цель и событие
6. Изучи логи для понимания flow: `docker compose logs -f orchestrator`

Удачи в разработке! 🚀
