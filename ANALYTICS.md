# Analytics & Metrics Documentation

Документация по аналитике Telegram бота в Mixpanel (EU регион)

## События (Events)

### 1. **Bot Started**
Срабатывает когда пользователь впервые запускает бота `/start`

**Properties:**
- `username` (string) - юзернейм в Telegram
- `first_name` (string) - имя пользователя
- `language_code` (string) - язык пользователя (обычно "ru")

### 2. **Message Received**
Срабатывает при получении любого сообщения (текст или голос)

**Properties:**
- `message_type` (string) - тип сообщения: "text" или "voice"
- `message_length` (number) - длина текста в символах (только для text)
- `voice_duration` (number) - длительность голосового в секундах (только для voice)

### 3. **LLM Parse**
Срабатывает при парсинге сообщения пользователя через GPT-4o-mini

**Properties:**
- `model` (string) - модель OpenAI ("gpt-4o-mini")
- `intent` (string) - распознанный интент:
  - `small_talk` - обычная беседа
  - `event.search` - поиск событий
  - `event.mutate` - создание/изменение/удаление событий
  - `goal.search` - показать все цели
  - `goal.create` - создать новую цель
  - `goal.delete` - удалить цель
  - `goal.query` - показать прогресс по цели
  - `goal.update_step` - обновить статус шага
  - `product.search` - поиск продуктов
- `tokens_input` (number) - входные токены
- `tokens_output` (number) - выходные токены
- `tokens_total` (number) - всего токенов (input + output)
- `message_length` (number) - длина исходного сообщения
- **`cost_rub` (number)** - стоимость запроса в рублях

### 4. **LLM Generate Steps**
Срабатывает при автогенерации шагов для новой цели

**Properties:**
- `model` (string) - модель OpenAI ("gpt-4o-mini")
- `goal_title` (string) - название цели
- `steps_count` (number) - количество сгенерированных шагов
- `tokens_input` (number) - входные токены
- `tokens_output` (number) - выходные токены
- `tokens_total` (number) - всего токенов
- **`cost_rub` (number)** - стоимость генерации в рублях

### 5. **Voice Transcription**
Срабатывает при распознавании голосового сообщения через Whisper

**Properties:**
- `model` (string) - модель Whisper ("whisper-1")
- `audio_size_bytes` (number) - размер аудиофайла в байтах
- `audio_seconds` (number) - длительность аудио в секундах
- `transcription_length` (number) - длина транскрипции в символах
- **`cost_rub` (number)** - стоимость транскрипции в рублях

### 6. **Intent Executed**
Срабатывает после выполнения интента в Core сервисе

**Properties:**
- `intent` (string) - выполненный интент (см. список в LLM Parse)
- `success` (boolean) - успешность выполнения
- `state` (string) - состояние пользователя в боте

## User Properties (People)

Профиль пользователя в Mixpanel People:

- `$name` (string) - полное имя из Telegram
- `username` (string) - юзернейм
- `language` (string) - язык ("ru")
- `total_parse_tokens` (number) - общее количество токенов на парсинг
- `total_generation_tokens` (number) - общее количество токенов на генерацию шагов
- `total_messages` (number) - общее количество сообщений
- `total_voice_messages` (number) - общее количество голосовых сообщений
- **`total_cost_rub` (number)** - общая стоимость использования в рублях

## Рекомендуемые дашборды

### 📊 **User Activity Dashboard**

**Метрики:**
- Total unique users: `count unique(distinct_id)`
- Daily Active Users (DAU): `count unique(distinct_id) where event="Message Received" group by day`
- Weekly Active Users (WAU): `count unique(distinct_id) where event="Message Received" group by week`
- Messages per user: `count(Message Received) / count unique(distinct_id)`
- Most active users: `count(Message Received) group by distinct_id order by count desc`

**Графики:**
- DAU/WAU trend line (last 30 days)
- User retention cohort
- Top 10 active users (bar chart)

---

### 💬 **Message Analytics Dashboard**

**Метрики:**
- Total messages: `count(Message Received)`
- Text messages: `count(Message Received where message_type="text")`
- Voice messages: `count(Message Received where message_type="voice")`
- Avg message length: `avg(message_length) where message_type="text"`
- Avg voice duration: `avg(voice_duration) where message_type="voice"`

**Графики:**
- Messages by type (pie chart: text vs voice)
- Message volume by hour of day
- Average message length trend

---

### 🤖 **LLM Usage Dashboard**

**Метрики:**
- Total LLM requests: `count(LLM Parse) + count(LLM Generate Steps)`
- Total tokens used: `sum(tokens_total from LLM Parse) + sum(tokens_total from LLM Generate Steps)`
- Average tokens per parse: `avg(tokens_total from LLM Parse)`
- Parse requests by model: `count(LLM Parse) group by model`
- Total LLM cost: `sum(cost_rub from LLM Parse) + sum(cost_rub from LLM Generate Steps)`

**Графики:**
- Daily token usage (stacked: input vs output)
- Cost trend over time (line chart)
- Tokens by user (top 10)

---

### 🎯 **Intent Analytics Dashboard**

**Метрики:**
- Total intents: `count(Intent Executed)`
- Intent success rate: `count(Intent Executed where success=true) / count(Intent Executed) * 100`
- Most popular intents: `count(LLM Parse) group by intent order by count desc`
- Failed intents: `count(Intent Executed where success=false) group by intent`

**Графики:**
- Intent distribution (pie chart)
- Success rate by intent type (bar chart)
- Intent usage over time (stacked area)

**Top intents to track:**
1. `small_talk` - беседа
2. `goal.create` - создание целей
3. `event.search` - поиск событий
4. `goal.query` - проверка прогресса
5. `goal.update_step` - обновление шагов

---

### 🎤 **Voice Usage Dashboard**

**Метрики:**
- Total voice messages: `count(Voice Transcription)`
- Total audio duration: `sum(audio_seconds from Voice Transcription)`
- Average audio size: `avg(audio_size_bytes from Voice Transcription)`
- Total transcription cost: `sum(cost_rub from Voice Transcription)`
- Voice users: `count unique(distinct_id from Voice Transcription)`

**Графики:**
- Voice messages trend (daily)
- Audio duration distribution (histogram)
- Voice vs text ratio

---

### 💰 **Cost Tracking Dashboard**

**Метрики:**
- **Total cost**: `sum(cost_rub)` across all events
- **Cost by service**:
  - LLM Parse: `sum(cost_rub from LLM Parse)`
  - LLM Generate Steps: `sum(cost_rub from LLM Generate Steps)`
  - Voice Transcription: `sum(cost_rub from Voice Transcription)`
- **Cost per user**: `sum(cost_rub) group by distinct_id`
- **Average cost per message**: `sum(cost_rub) / count(Message Received)`
- **Most expensive users**: `sum(cost_rub) group by distinct_id order by sum desc`

**Графики:**
- Daily cost trend (line chart)
- Cost breakdown by service (pie chart: Parse vs Generate vs Transcription)
- Top 10 expensive users (bar chart)
- Cost per user distribution (histogram)

**Формулы для расчета:**
```
Total Daily Cost =
  sum(cost_rub from LLM Parse) +
  sum(cost_rub from LLM Generate Steps) +
  sum(cost_rub from Voice Transcription)
```

---

### 🎯 **Goal Analytics Dashboard**

**Метрики:**
- Total goals created: `count(LLM Generate Steps)`
- Average steps per goal: `avg(steps_count from LLM Generate Steps)`
- Goal creation cost: `sum(cost_rub from LLM Generate Steps)`
- Users with goals: `count unique(distinct_id from LLM Generate Steps)`

**Графики:**
- Goals created over time
- Steps distribution (histogram of steps_count)
- Goal creation cost trend

---

## Прайсинг (для справки)

Все цены в рублях за 1M токенов (источник: ProxyAPI, октябрь 2025)

### OpenAI Models
- **gpt-4o-mini** (основная модель бота):
  - Input: 36.72 ₽/1M tokens
  - Output: 146.88 ₽/1M tokens
  - Cache: 18.36 ₽/1M tokens

### Audio
- **whisper-1** (распознавание речи):
  - 1.47 ₽/1M секунд аудио

### Примеры расчета стоимости

**LLM Parse (типичный запрос):**
- Input: 500 tokens × 36.72 ₽/1M = 0.01836 ₽
- Output: 100 tokens × 146.88 ₽/1M = 0.01469 ₽
- **Итого: ~0.033 ₽ за запрос**

**Voice Transcription (30 сек аудио):**
- 30 секунд × 1.47 ₽/1M = 0.0000441 ₽
- **Итого: ~0.00004 ₽ за 30 сек**

**Generate Steps (создание цели с 5 шагами):**
- Input: 800 tokens × 36.72 ₽/1M = 0.02938 ₽
- Output: 400 tokens × 146.88 ₽/1M = 0.05875 ₽
- **Итого: ~0.088 ₽ за генерацию**

## Алерты (рекомендуется настроить)

1. **Высокая стоимость пользователя**
   - Alert: `sum(cost_rub) group by distinct_id > 10 ₽`
   - Проверять ежедневно

2. **Резкий рост затрат**
   - Alert: `sum(cost_rub today) > sum(cost_rub yesterday) * 2`
   - Может указывать на проблемы или спам

3. **Низкий Success Rate интентов**
   - Alert: `success_rate(Intent Executed) < 80%`
   - Проверять качество парсинга

4. **Аномальное использование токенов**
   - Alert: `avg(tokens_total from LLM Parse) > 2000`
   - Возможно, слишком длинные промпты

## Экспорт данных

Mixpanel поддерживает экспорт через:
- Raw Data Export API
- Scheduled Reports (email)
- Data Pipelines (webhook)

Все данные хранятся в EU регионе (api-eu.mixpanel.com).
