from jinja2 import Template

SCHEDULE_GOAL_PROMPT_TEMPLATE = Template("""
Пользователь хочет запланировать шаги цели: "{{ goal_title }}"

Шаги цели (всего {{ steps|length }}):
{% for step in steps %}
ID: {{ step.id }}, Порядок: {{ step.order }}. {{ step.title }} (время: {{ step.estimated_hours }}ч)
{% endfor %}

Параметры планирования:
- Начальная дата: {{ start_date }}
- Deadline: {{ deadline }}
- Предпочитаемое время работы: {{ preferred_times|join(", ") if preferred_times else "любое" }}
- Предпочитаемые дни: {{ preferred_days|join(", ") if preferred_days else "любые" }}
- Длительность одной сессии: {{ duration_minutes }} минут

Существующие события пользователя (занятые слоты):
{% if existing_events %}
{% for event in existing_events %}
- {{ event.date }} в {{ event.time if event.time else "весь день" }}: {{ event.title }}
{% endfor %}
{% else %}
- Нет занятых слотов
{% endif %}

Свободные временные слоты:
{% if free_slots %}
{% for slot in free_slots[:20] %}
- {{ slot.date }} в {{ slot.time }} ({{ slot.duration_minutes }} мин)
{% endfor %}
{% if free_slots|length > 20 %}
... и еще {{ free_slots|length - 20 }} слотов
{% endif %}
{% else %}
- Нет свободных слотов найдено
{% endif %}

ВАЖНО: При планировании учитывай:
1. **Dependencies между шагами**: Шаги должны выполняться последовательно (order).
   - Шаг 2 нельзя планировать раньше Шага 1
   - Соблюдай порядок выполнения

2. **Равномерное распределение**: Распредели шаги равномерно от start_date до deadline
   - Не накапливай все шаги в начале или конце
   - Оставь буфер на случай непредвиденных обстоятельств

3. **Избегай конфликтов**: Не планируй шаги на время существующих событий

4. **Реалистичность**:
   - Если шаг требует 5 часов, а доступно только 2-часовые слоты, раздели на несколько сессий
   - Учитывай, что человеку нужен отдых между сессиями

Верни JSON массив с расписанием (используй НАСТОЯЩИЕ ID шагов из списка выше, НЕ порядковый номер):
[
  {"step_id": <ID_первого_шага>, "planned_date": "2025-11-15", "planned_time": "10:00"},
  {"step_id": <ID_второго_шага>, "planned_date": "2025-11-17", "planned_time": "14:00"},
  ...
]

Если невозможно уложиться в deadline, верни пустой массив [] и объяснение в поле "reason".
""")
