# Тестовая страница MaxOn Mini-App

## 🔗 URLs

### Основное приложение:
- Production: `https://mini-2a3lrea9p-0stg0ts-projects.vercel.app`
- Local: `http://localhost:5173`

### Тестовая страница:
- Production: `https://mini-8p7bip7du-0stg0ts-projects.vercel.app/test.html`
- Local: `http://localhost:5173/test.html`

## 🧪 Как использовать тестовую страницу

### Вариант 1: Через браузер (без MAX messenger)

Просто открой в браузере:
```
https://mini-8p7bip7du-0stg0ts-projects.vercel.app/test.html
```

**Что покажет:**
- ❌ MAX WebApp SDK не будет загружен (нормально для браузера)
- ✅ Будет использован Demo User ID: `89578356`
- ✅ Можно протестировать API запросы к бэкенду

**Доступные действия:**
1. **Загрузить цели** - GET запрос к `http://localhost:8104/api/goals?user_id=89578356`
2. **Загрузить события** - GET запрос к `http://localhost:8104/api/events?user_id=89578356`
3. **Отправить сообщение** - POST запрос к `http://localhost:8101/api/process`

### Вариант 2: Через MAX messenger (реальный user_id)

Для этого нужно зарегистрировать WebApp:

1. Открой MAX messenger
2. Найди **@MasterBot**
3. Отправь: `/mybots`
4. Выбери **@t623_hakaton_bot**
5. Отправь: `/setwebapp`
6. Введи URL: `https://mini-8p7bip7du-0stg0ts-projects.vercel.app/test.html`
7. Открой бота и запусти WebApp

**Что покажет:**
- ✅ MAX WebApp SDK загружен
- ✅ Твой реальный User ID из MAX
- ✅ Твое имя, username из MAX profile
- ✅ API запросы будут использовать твой user_id

## 📊 Что показывает тестовая страница

### 1. MAX WebApp Info
- Статус SDK (загружен/не загружен)
- Платформа (ios/android/web)
- Версия SDK
- Состояние (expanded/collapsed)

### 2. User Info
- User ID (из MAX или demo)
- Имя и фамилия
- Username
- Язык

### 3. API Requests
Три кнопки для тестирования API:

#### Загрузить цели
```javascript
GET http://localhost:8104/api/goals?user_id={userId}
```
Покажет все цели пользователя с шагами и прогрессом.

#### Загрузить события
```javascript
GET http://localhost:8104/api/events?user_id={userId}
```
Покажет все события пользователя.

#### Отправить сообщение
```javascript
POST http://localhost:8101/api/process
Body: {
  "user_id": "{userId}",
  "message": "Покажи мои цели",
  "context": {}
}
```
Отправит сообщение в orchestrator и покажет ответ LLM.

### 4. Raw Data (Debug)
Показывает полный `initDataUnsafe` объект от MAX WebApp SDK в JSON формате.

## 🔧 Локальное тестирование

1. Запусти бэкенд:
```bash
cd /Users/asgatakmaev/Desktop/business/maxOn
docker compose up -d
```

2. Запусти mini-app локально:
```bash
cd services/mini-app
npm run dev
```

3. Открой тестовую страницу:
```
http://localhost:5173/test.html
```

4. Проверь что:
   - Core API доступен: http://localhost:8104/docs
   - Orchestrator доступен: http://localhost:8101/docs

## 🐛 Troubleshooting

### API запросы не работают

**Ошибка:** `Failed to fetch` или CORS error

**Решение:**
1. Убедись что бэкенд запущен:
   ```bash
   docker compose ps
   ```

2. Проверь что сервисы доступны:
   ```bash
   curl http://localhost:8104/api/goals?user_id=89578356
   curl http://localhost:8101/health
   ```

3. Если используешь production URL (`mini-8p7bip7du-0stg0ts-projects.vercel.app`):
   - API на localhost не доступны из Vercel
   - Нужно задеплоить бэкенд на публичный URL
   - Или использовать ngrok для временного доступа

### MAX WebApp SDK не загружается

**В браузере:** Это нормально, SDK работает только внутри MAX messenger.

**В MAX messenger:**
1. Проверь что URL зарегистрирован через @MasterBot
2. Проверь что используешь HTTPS (Vercel дает автоматически)
3. Открой Developer Tools и проверь Console на ошибки

## 📝 Примеры запросов

### CURL примеры для тестирования API:

```bash
# Получить цели пользователя
curl "http://localhost:8104/api/goals?user_id=89578356"

# Получить события
curl "http://localhost:8104/api/events?user_id=89578356"

# Отправить сообщение в чат
curl -X POST "http://localhost:8101/api/process" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "89578356",
    "message": "Покажи мои цели",
    "context": {}
  }'

# Создать новую цель
curl -X POST "http://localhost:8104/api/goals" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "89578356",
    "title": "Выучить Python",
    "description": "Пройти курс по Python",
    "target_date": "2025-12-31",
    "category": "Обучение",
    "priority": "high"
  }'
```

## 🚀 Production deployment

Когда бэкенд будет на production, обнови URL в `test.html`:

```javascript
const CORE_API_URL = 'https://your-backend.com:8104';
const ORCHESTRATOR_API_URL = 'https://your-backend.com:8101';
```

Затем задеплой:
```bash
cd services/mini-app
vercel --prod --yes
```

## 📖 Дополнительно

- Основная документация: [DEPLOY.md](./DEPLOY.md)
- WebApp регистрация: [/WEBAPP_REGISTRATION.md](../../WEBAPP_REGISTRATION.md)
- Vercel Dashboard: https://vercel.com/0stg0ts-projects/mini-app
