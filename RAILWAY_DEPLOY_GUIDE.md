# Инструкция по деплою Context и LLM сервисов на Railway

## Текущая ситуация
✅ **Уже развернуто на Railway:**
- Core Service: `https://bountiful-solace-production.up.railway.app`
- Orchestrator Service: `https://maxon-production.up.railway.app`
- PostgreSQL Database

❌ **Нужно развернуть:**
- Context Service (порт 8002)
- LLM Service (порт 8003)

## Шаг 1: Подключиться к GitHub репозиторию

1. Откройте [Railway Dashboard](https://railway.app/dashboard)
2. Выберите ваш проект (где уже развернуты Core и Orchestrator)
3. Нажмите "New Service" → "GitHub Repo"
4. Выберите репозиторий `InTeam-Solutions/maxOn` (или как он называется)

## Шаг 2: Развернуть Context Service

### 2.1 Создать новый сервис
1. Нажмите "+ New" → "GitHub Repo"
2. Выберите ваш репозиторий
3. Назовите сервис: **context**

### 2.2 Настроить Dockerfile
В настройках сервиса:
- **Root Directory**: оставьте пустым (используется корень)
- **Dockerfile Path**: `services/context/Dockerfile`
- **Build Command**: оставьте пустым (используется Dockerfile)

### 2.3 Настроить Environment Variables
Добавьте следующие переменные окружения:

```bash
# Database (используйте переменную из вашего Railway PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (если есть Redis на Railway, иначе можно добавить новый)
REDIS_URL=redis://redis:6379/1

# Core Service (URL вашего Core сервиса)
CORE_SERVICE_URL=https://bountiful-solace-production.up.railway.app

# Logging
LOG_LEVEL=INFO
```

### 2.4 Настроить порт
- **Port**: 8002 (Railway автоматически определит из EXPOSE в Dockerfile)

### 2.5 Deploy
Нажмите "Deploy" и дождитесь успешного деплоя

## Шаг 3: Развернуть LLM Service

### 3.1 Создать новый сервис
1. Нажмите "+ New" → "GitHub Repo"
2. Выберите ваш репозиторий
3. Назовите сервис: **llm**

### 3.2 Настроить Dockerfile
В настройках сервиса:
- **Root Directory**: оставьте пустым
- **Dockerfile Path**: `services/llm/Dockerfile`

### 3.3 Настроить Environment Variables
```bash
# OpenAI API
OPENAI_API_KEY=sk-zGoQL65hwYo4oF9If5DVpohLQsHufUkv
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
OPENAI_CHAT_MODEL=gpt-4o-mini

# Redis (если есть)
REDIS_URL=redis://redis:6379/2

# Logging
LOG_LEVEL=INFO
```

### 3.4 Deploy
Нажмите "Deploy"

## Шаг 4: Обновить Orchestrator Environment Variables

После того как Context и LLM сервисы развернуты, вам нужно обновить переменные в **Orchestrator**:

1. Откройте настройки **Orchestrator** сервиса
2. Добавьте/обновите переменные:

```bash
# Context Service (замените URL на тот, что Railway выдаст вашему context сервису)
CONTEXT_SERVICE_URL=https://your-context-service.up.railway.app

# LLM Service (замените URL на тот, что Railway выдаст вашему llm сервису)
LLM_SERVICE_URL=https://your-llm-service.up.railway.app

# Core Service (уже должно быть настроено)
CORE_SERVICE_URL=https://bountiful-solace-production.up.railway.app
```

3. После сохранения переменных Orchestrator автоматически перезапустится

## Шаг 5: Настроить PostgreSQL (если нужно)

Если у вас еще нет PostgreSQL на Railway:

1. Нажмите "+ New" → "Database" → "PostgreSQL"
2. Railway создаст базу данных
3. В настройках Postgres найдите переменную `DATABASE_URL`
4. Скопируйте её и используйте в Context и Core сервисах

## Шаг 6: Настроить Redis (опционально)

Если нужен Redis:

1. Нажмите "+ New" → "Database" → "Redis"
2. Railway создаст Redis
3. Используйте переменную `REDIS_URL` в ваших сервисах

## Шаг 7: Проверить деплой

После того как все сервисы развернуты, проверьте их:

### 7.1 Проверить healthcheck каждого сервиса
```bash
# Context
curl https://your-context-service.up.railway.app/health

# LLM
curl https://your-llm-service.up.railway.app/health

# Orchestrator (уже работает)
curl https://maxon-production.up.railway.app/health
```

### 7.2 Протестировать chat
```bash
curl -X POST 'https://maxon-production.up.railway.app/api/process' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"89578356","message":"хочу подготовиться к кр по дифурам"}'
```

Должен вернуться нормальный ответ с созданием цели, а не "LLM parsing failed".

## Возможные проблемы и решения

### Проблема 1: Ошибка билда Dockerfile
**Причина**: Dockerfile использует `COPY shared/`
**Решение**: Убедитесь что Root Directory = пустой (используется корень репозитория)

### Проблема 2: Database connection failed
**Причина**: Неправильный DATABASE_URL
**Решение**: Используйте переменную `${{Postgres.DATABASE_URL}}` из вашего PostgreSQL сервиса

### Проблема 3: Service cannot connect to другому сервису
**Причина**: Неправильные URL в environment variables
**Решение**: Убедитесь что используете полные HTTPS URLs (например `https://service.up.railway.app`)

### Проблема 4: Redis connection failed
**Причина**: Redis использует внутренние Docker URLs
**Решение**: На Railway используйте переменную `${{Redis.REDIS_URL}}` если есть Redis сервис

## Итоговая архитектура на Railway

После деплоя у вас будет:

```
┌─────────────────────────────────────────────┐
│  Railway Project                             │
├─────────────────────────────────────────────┤
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │PostgreSQL│  │  Redis   │  │   Core   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │              │        │
│  ┌────┴──────────┬──┴──────────────┴─────┐  │
│  │              │                        │  │
│  │   Context    │        LLM            │  │
│  │   Service    │      Service          │  │
│  └──────┬───────┴────────┬──────────────┘  │
│         │                │                  │
│  ┌──────┴────────────────┴───────┐         │
│  │      Orchestrator              │         │
│  └────────────────────────────────┘         │
│                                              │
└─────────────────────────────────────────────┘
           ▲
           │
    ┌──────┴──────┐
    │   Vercel    │
    │  Mini-App   │
    └─────────────┘
```

## URLs для справки

- **Core**: `https://bountiful-solace-production.up.railway.app`
- **Orchestrator**: `https://maxon-production.up.railway.app`
- **Context**: (будет после деплоя)
- **LLM**: (будет после деплоя)

---

## После завершения деплоя

Когда все сервисы будут развернуты и работают, вернитесь в проект и дайте мне знать URL адреса Context и LLM сервисов, чтобы я мог помочь обновить конфигурацию Orchestrator.
