# Деплой MaxOn на Railway

## Шаг 1: Залогинься в Railway

```bash
railway login
```

Это откроет браузер для авторизации через GitHub.

## Шаг 2: Создай новый проект

```bash
railway init
```

Выбери:
- **Create a new project** → Yes
- **Project name** → `maxon`

## Шаг 3: Добавь PostgreSQL

В Railway Dashboard (откроется автоматически):
1. Нажми **"+ New"** → **Database** → **Add PostgreSQL**
2. Подожди пока база развернется (1-2 минуты)
3. Скопируй `DATABASE_URL` из переменных окружения

Или через CLI:
```bash
railway add --database postgres
```

## Шаг 4: Задеплой Core Service

```bash
cd services/core
railway up
```

После деплоя:
1. Перейди в Railway Dashboard → Core service
2. Добавь переменные окружения:
   ```
   DATABASE_URL=${DATABASE_URL}  # Ссылка на PostgreSQL из шага 3
   REDIS_URL=redis://redis:6379/0
   PORT=8004
   ```
3. В настройках → **Generate Domain** → скопируй URL (например: `core-production.up.railway.app`)

## Шаг 5: Задеплой Orchestrator

```bash
cd ../orchestrator
railway up
```

Добавь переменные окружения:
```
CORE_SERVICE_URL=https://core-production.up.railway.app
LLM_SERVICE_URL=http://llm:8003
CONTEXT_SERVICE_URL=http://context:8002
PORT=8001
```

Generate Domain для Orchestrator → скопируй URL

## Шаг 6: Обнови Vercel Environment Variables

Перейди на https://vercel.com/0stg0ts-projects/mini-app/settings/environment-variables

Обнови переменные:
```
VITE_CORE_API_URL=https://core-production.up.railway.app
VITE_ORCHESTRATOR_API_URL=https://orchestrator-production.up.railway.app
VITE_USE_REAL_API=true
```

Сохрани и **Redeploy** последний деплой.

## Шаг 7: Протестируй

1. Открой бота @t623_hakaton_bot
2. Отправь `/webapp`
3. Нажми на ссылку
4. Теперь должны загружаться твои реальные цели из базы!

---

## Альтернативный способ: Деплой через Railway Dashboard (Web UI)

### 1. Создай новый проект
1. Открой https://railway.app/new
2. Нажми **"Deploy from GitHub repo"**
3. Подключи свой GitHub аккаунт
4. Выбери репозиторий `maxOn`

### 2. Добавь PostgreSQL
1. В проекте нажми **"+ New"**
2. Выбери **Database** → **PostgreSQL**
3. Подожди пока развернется

### 3. Добавь Core Service
1. Нажми **"+ New"** → **GitHub Repo**
2. Выбери папку `services/core`
3. В настройках:
   - **Root Directory**: `services/core`
   - **Build Command**: (оставь пустым, используется Dockerfile)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. Добавь переменные окружения (вкладка Variables):
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   PORT=8004
   ```

5. Generate Domain

### 4. Добавь Orchestrator
Повтори шаг 3, но для `services/orchestrator`

Переменные:
```
CORE_SERVICE_URL=https://твой-core-url.up.railway.app
PORT=8001
```

---

## Troubleshooting

### Сервис не запускается

1. Проверь логи:
   ```bash
   railway logs
   ```

2. Убедись что все переменные окружения установлены

3. Проверь что Dockerfile правильно собирается локально:
   ```bash
   docker build -t test-core services/core
   docker run -p 8004:8004 test-core
   ```

### DATABASE_URL не работает

Railway автоматически создает переменную `DATABASE_URL` когда добавляешь PostgreSQL.

Проверь что она доступна:
```bash
railway variables
```

### Приложение показывает 502/503

Это значит сервис еще не запустился. Подожди 2-3 минуты после деплоя.

---

## Полезные команды

```bash
# Посмотреть статус сервисов
railway status

# Посмотреть логи
railway logs

# Посмотреть переменные окружения
railway variables

# Открыть Railway Dashboard
railway open

# Удалить проект
railway delete
```
