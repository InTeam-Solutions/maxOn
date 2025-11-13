# Регистрация WebApp в MAX messenger

## Что нужно сделать

Чтобы подключить mini-app к вашему боту @t623_hakaton_bot, следуй этим шагам:

### Шаг 1: Задеплой mini-app

Сначала задеплой mini-app на публичный https:// URL.

**Вариант А: Vercel (рекомендуется)**

```bash
cd services/mini-app
npm install -g vercel
vercel login
vercel --prod
```

Vercel выдаст URL типа: `https://maxon-mini-app.vercel.app`

**Вариант Б: Ngrok (для тестирования)**

```bash
# В одном терминале запусти mini-app
cd services/mini-app
npm run dev

# В другом терминале
ngrok http 5173
```

Ngrok выдаст URL типа: `https://abc123.ngrok.io`

### Шаг 2: Зарегистрируй WebApp в боте через @MasterBot

1. Открой MAX messenger
2. Найди бота **@MasterBot** (это бот для управления другими ботами)
3. Отправь команду:
   ```
   /mybots
   ```

4. Выбери своего бота **@t623_hakaton_bot** из списка

5. Нажми **"Web App"** или отправь:
   ```
   /setwebapp
   ```

6. Введи URL твоего задеплоенного mini-app:
   ```
   https://maxon-mini-app.vercel.app
   ```
   (или твой ngrok URL)

7. Подтверди регистрацию

### Шаг 3: Добавь кнопку WebApp в бота

Есть два способа добавить кнопку для запуска WebApp:

**Способ А: Через клавиатуру (ReplyKeyboardMarkup)**

Добавь этот код в `services/api-gateway/app/main.py`:

```python
from maxapi.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

def main_menu_keyboard_with_webapp():
    webapp_button = KeyboardButton(
        text="🚀 Открыть MaxOn App",
        web_app=WebAppInfo(url="https://твой-url.vercel.app")
    )

    return ReplyKeyboardMarkup(
        keyboard=[
            [webapp_button],
            [
                KeyboardButton(text="🎯 Мои цели"),
                KeyboardButton(text="📅 Календарь")
            ],
            [
                KeyboardButton(text="➕ Новая цель"),
                KeyboardButton(text="➕ Событие")
            ]
        ],
        resize_keyboard=True
    )
```

Затем используй эту клавиатуру при отправке сообщений.

**Способ Б: Через Inline кнопку (InlineKeyboardMarkup)**

```python
from maxapi.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def inline_webapp_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Открыть MaxOn App",
                web_app=WebAppInfo(url="https://твой-url.vercel.app")
            )]
        ]
    )
```

### Шаг 4: Настрой переменные окружения для production

В `services/mini-app/.env`:

```env
# Production URLs
VITE_CORE_API_URL=https://твой-бэкенд.com:8104
VITE_ORCHESTRATOR_API_URL=https://твой-бэкенд.com:8101
VITE_USE_REAL_API=true
```

Пересобери:
```bash
npm run build
vercel --prod
```

### Шаг 5: Протестируй WebApp

1. Открой бота @t623_hakaton_bot в MAX messenger
2. Нажми на кнопку **"🚀 Открыть MaxOn App"**
3. Mini-app должен открыться внутри MAX messenger
4. Проверь что:
   - Дизайн отображается корректно
   - API запросы работают (Goals загружаются)
   - Чат работает с реальным LLM

## Альтернативный способ: Через команду

Можно также добавить команду `/webapp` в бота:

```python
@dp.message_callback(F.callback.payload == "open_webapp")
async def open_webapp(callback: MessageCallback):
    webapp_button = InlineKeyboardButton(
        text="🚀 Открыть приложение",
        web_app=WebAppInfo(url="https://твой-url.vercel.app")
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])

    await callback.message.answer(
        "Нажми кнопку ниже, чтобы открыть MaxOn App:",
        reply_markup=keyboard
    )
```

## Troubleshooting

### WebApp не открывается

1. **Проверь что URL на https://**
   - MAX требует защищённое соединение
   - Ngrok автоматически даёт https
   - Vercel тоже даёт https

2. **Проверь что URL зарегистрирован в @MasterBot**
   - Используй `/setwebapp` для регистрации
   - URL должен совпадать с тем, что в коде

3. **Проверь CORS на бэкенде**
   - Должен быть разрешён origin WebApp URL
   - Мы уже добавили `allow_origins=["*"]` для development

### API запросы не работают в WebApp

1. **Проверь что бэкенд доступен по https://**
   - Если бэкенд на http://localhost - он недоступен из WebApp
   - Нужно задеплоить бэкенд на публичный https:// URL
   - Или использовать ngrok для бэкенда тоже

2. **Mixed content error**
   - WebApp на https:// не может вызывать http:// API
   - Решение: задеплой бэкенд на https

### User ID не передаётся

Проверь в консоли браузера:
```javascript
window.MaxWebApp.initDataUnsafe.user
```

Если undefined - значит WebApp SDK не загрузился. Проверь:
1. `VITE_MAX_WEB_APP_SRC` правильно установлен
2. Network tab - загружается ли `max-web-app.js`

## Следующие шаги

После успешной регистрации:

- [ ] Задеплой бэкенд на production (с https://)
- [ ] Обнови URLs в mini-app `.env`
- [ ] Пересобери и задеплой mini-app
- [ ] Протестируй все фичи в реальном MAX messenger
- [ ] Настрой production CORS (не `*`, а конкретные origins)
- [ ] Добавь мониторинг и логирование
