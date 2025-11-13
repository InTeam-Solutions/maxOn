# MaxOn WebApp Setup Guide

## Что сделано

✅ Красивый респонсивный дизайн с плавными переходами
✅ API клиент для Core Service и Orchestrator
✅ Интеграция чата с реальным LLM через Orchestrator
✅ Аутентификация через MAX WebApp SDK
✅ CORS настроен на бэкенде
✅ Docker контейнер для деплоя

## Как запустить локально

### Development mode (с моками)

```bash
cd services/mini-app
npm install
npm run dev
```

Откроется на http://localhost:5173

### Production build

```bash
npm run build
npm run preview
```

### Docker

```bash
# Из корня проекта
docker compose up mini-app
```

Откроется на http://localhost:5173

## Настройка переменных окружения

Создайте `.env` файл в `services/mini-app/`:

```env
# MAX WebApp SDK
VITE_MAX_WEB_APP_SRC=https://static.maxhub.com/sdk/max-web-app.js

# API URLs
VITE_CORE_API_URL=http://localhost:8104
VITE_ORCHESTRATOR_API_URL=http://localhost:8101

# Включить реальный API вместо моков
VITE_USE_REAL_API=true

# Demo user для разработки (когда не в MAX messenger)
VITE_DEMO_USER_ID=89578356
```

## Регистрация WebApp в MAX messenger

### Шаг 1: Деплой mini-app

Задеплойте mini-app на доступный извне URL. Варианты:

1. **Vercel / Netlify** (рекомендуется для фронтенда):
   ```bash
   cd services/mini-app
   npm run build
   # Загрузите dist/ на Vercel/Netlify
   ```

2. **VPS с nginx**:
   ```bash
   docker compose up -d mini-app
   # Настройте nginx reverse proxy на 5173 порт
   ```

3. **Ngrok для тестирования**:
   ```bash
   ngrok http 5173
   # Получите https://xxx.ngrok.io URL
   ```

### Шаг 2: Зарегистрируйте WebApp в MAX

1. Откройте MAX messenger
2. Найдите вашего бота @t623_hakaton_bot
3. Отправьте команду боту (или используйте MAX Bot API):

```
/setwebapp
```

4. Укажите URL вашего задеплоенного mini-app:
```
https://your-mini-app-url.com
```

### Шаг 3: Добавьте кнопку запуска WebApp в бота

Обновите API Gateway для добавления кнопки:

```python
# services/api-gateway/app/main.py

from maxapi.types import WebAppInfo, KeyboardButton, ReplyKeyboardMarkup

# Добавьте кнопку WebApp
webapp_button = KeyboardButton(
    text="🚀 Открыть MaxOn App",
    web_app=WebAppInfo(url="https://your-mini-app-url.com")
)

keyboard = ReplyKeyboardMarkup(
    keyboard=[[webapp_button]],
    resize_keyboard=True
)

# Отправьте с сообщением
await bot.send_message(
    chat_id=user_id,
    text="Привет! Открой наше приложение:",
    reply_markup=keyboard
)
```

### Шаг 4: Настройте Production API URLs

В `.env` mini-app укажите production URLs бэкенда:

```env
VITE_CORE_API_URL=https://your-backend.com:8104
VITE_ORCHESTRATOR_API_URL=https://your-backend.com:8101
VITE_USE_REAL_API=true
```

Пересоберите:
```bash
npm run build
```

## Проверка интеграции

### 1. Проверьте MAX WebApp SDK

Откройте консоль браузера в WebApp:
```javascript
console.log(window.MaxWebApp)
console.log(window.MaxWebApp.initDataUnsafe)
```

Должно показать:
```javascript
{
  user: { id: 89578356, first_name: "...", ... },
  auth_date: 1234567890,
  hash: "..."
}
```

### 2. Проверьте API connectivity

В консоли:
```javascript
fetch('http://localhost:8104/health')
  .then(r => r.json())
  .then(console.log)
```

Должно вернуть:
```json
{"status": "healthy", "service": "core"}
```

### 3. Проверьте чат

Напишите сообщение в чате mini-app. В консоли должны быть логи:
```
[MaxOn] API client configured with user_id: 89578356
[MaxOn] Sending message to orchestrator...
```

## Troubleshooting

### CORS errors

Если видите CORS ошибки в консоли:

1. Проверьте что backend services перезапущены с новыми CORS настройками:
   ```bash
   docker compose restart core orchestrator
   ```

2. Проверьте что CORS middleware добавлен в `services/core/app/main.py` и `services/orchestrator/app/main.py`

### MAX WebApp SDK не загружается

1. Проверьте что `VITE_MAX_WEB_APP_SRC` правильно установлен
2. Откройте Network tab в DevTools - должен быть запрос к `https://static.maxhub.com/sdk/max-web-app.js`
3. Если SDK недоступен, используйте fallback (demo user автоматически)

### API запросы не работают

1. Проверьте что backend services запущены:
   ```bash
   docker compose ps
   ```

2. Проверьте логи:
   ```bash
   docker compose logs -f core orchestrator
   ```

3. Проверьте `.env` файл - правильные ли URLs

## Production Deployment Checklist

- [ ] Mini-app задеплоен на https:// URL
- [ ] Backend API доступен по https:// (нужен SSL сертификат)
- [ ] CORS настроен на specific origins (не `*`)
- [ ] WebApp зарегистрирован в MAX messenger
- [ ] Кнопка WebApp добавлена в бота
- [ ] `.env` переменные указывают на production URLs
- [ ] `VITE_USE_REAL_API=true` установлен
- [ ] Протестировано в реальном MAX messenger

## Дальнейшие улучшения

- [ ] Заменить моки целей на реальные API вызовы к Core Service
- [ ] Добавить pull-to-refresh для обновления данных
- [ ] Добавить offline mode с кэшированием
- [ ] Добавить push notifications через MAX WebApp API
- [ ] Добавить share functionality для целей
- [ ] Оптимизировать bundle size (code splitting)
