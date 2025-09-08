# Initio

Простой прототип бэкенда для чат-бота.

## Запуск

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

## Telegram бот

```bash
export TELEGRAM_TOKEN=<токен>
python telegram_bot.py
```

## Тесты

```bash
pytest
```
