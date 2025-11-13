# Деплой MaxOn Mini-App на Vercel

## Шаг 1: Авторизуйся в Vercel

```bash
cd /Users/asgatakmaev/Desktop/business/maxOn/services/mini-app
vercel login
```

Vercel откроет браузер для авторизации. Войди через:
- GitHub (рекомендуется)
- GitLab
- Bitbucket
- Email

## Шаг 2: Задеплой проект

```bash
vercel --prod
```

Vercel задаст несколько вопросов:

1. **Set up and deploy?** → `Y` (yes)
2. **Which scope?** → выбери свой аккаунт
3. **Link to existing project?** → `N` (no, создаём новый)
4. **What's your project's name?** → `maxon-mini-app` (или любое имя)
5. **In which directory is your code located?** → `./` (текущая директория)
6. **Want to override settings?** → `N` (no, используем vercel.json)

После деплоя Vercel выдаст URL:
```
✅ Production: https://maxon-mini-app.vercel.app
```

## Шаг 3: Настрой переменные окружения

⚠️ **ВАЖНО:** На момент первого деплоя у тебя уже есть рабочий URL:
`https://mini-2a3lrea9p-0stg0ts-projects.vercel.app`

Настрой переменные окружения в Vercel Dashboard:

1. Открой в браузере: https://vercel.com/0stg0ts-projects/mini-app/settings/environment-variables
2. Добавь переменные:

```
VITE_MAX_WEB_APP_SRC=https://static.maxhub.com/sdk/max-web-app.js
VITE_CORE_API_URL=http://localhost:8104
VITE_ORCHESTRATOR_API_URL=http://localhost:8101
VITE_USE_REAL_API=false
VITE_DEMO_USER_ID=89578356
```

**⚠️ ВАЖНО:** Пока бэкенд на localhost, установи `VITE_USE_REAL_API=false` (будут моки).

Когда бэкенд будет на production:
```
VITE_CORE_API_URL=https://your-backend.com:8104
VITE_ORCHESTRATOR_API_URL=https://your-backend.com:8101
VITE_USE_REAL_API=true
```

3. Нажми **Save**
4. Перейди в **Deployments** → нажми **Redeploy** для последнего деплоя

## Шаг 4: Зарегистрируй WebApp в MAX

1. Открой MAX messenger
2. Найди **@MasterBot**
3. Отправь: `/mybots`
4. Выбери **@t623_hakaton_bot**
5. Нажми **"Web App"** или отправь `/setwebapp`
6. Введи URL: `https://mini-2a3lrea9p-0stg0ts-projects.vercel.app`
7. Подтверди

## Шаг 5: Добавь кнопку WebApp в бота

Добавь в `services/api-gateway/app/main.py`:

```python
from maxapi.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

WEBAPP_URL = "https://mini-2a3lrea9p-0stg0ts-projects.vercel.app"  # Твой URL

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🚀 Открыть MaxOn App",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
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

Перезапусти бота:
```bash
cd /Users/asgatakmaev/Desktop/business/maxOn
docker compose restart api-gateway
```

## Шаг 6: Тестируй!

1. Открой бота @t623_hakaton_bot в MAX
2. Нажми кнопку **"🚀 Открыть MaxOn App"**
3. Mini-app откроется внутри MAX messenger!

## Обновление деплоя

Когда внёс изменения:

```bash
cd /Users/asgatakmaev/Desktop/business/maxOn/services/mini-app
vercel --prod
```

Vercel автоматически пересоберёт и задеплоит.

## Полезные команды

```bash
# Просмотр всех деплоев
vercel ls

# Логи последнего деплоя
vercel logs

# Удалить проект
vercel remove maxon-mini-app

# Открыть Dashboard в браузере
vercel open
```

## Troubleshooting

### Деплой не работает

1. Проверь что `package.json` и `vercel.json` на месте
2. Запусти `npm run build` локально - должно пройти без ошибок
3. Проверь логи: `vercel logs`

### WebApp показывает белый экран

1. Открой Developer Tools в MAX (если доступно)
2. Проверь Console - есть ли ошибки
3. Проверь что env variables установлены в Vercel
4. Попробуй Redeploy в Vercel Dashboard

### API запросы не работают

Нормально! Пока бэкенд на localhost, он недоступен из Vercel.

Решения:
1. Используй моки (`VITE_USE_REAL_API=false`)
2. Задеплой бэкенд на production (Railway, Render, AWS)
3. Используй ngrok для бэкенда:
   ```bash
   ngrok http 8104
   ngrok http 8101
   ```
   И обнови `VITE_CORE_API_URL` / `VITE_ORCHESTRATOR_API_URL` в Vercel

## Что дальше?

- [ ] Задеплой бэкенд на production
- [ ] Обнови env variables в Vercel
- [ ] Включи `VITE_USE_REAL_API=true`
- [ ] Настрой custom domain (опционально)
- [ ] Добавь analytics (Vercel Analytics)
