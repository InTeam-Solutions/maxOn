from jinja2 import Template

GOAL_STEPS_PROMPT_TEMPLATE = Template("""
Пользователь хочет достичь цели: "{{ goal_title }}"

Дополнительная информация:
- Текущий уровень: {{ current_level or "не указан" }}
- Время в неделю: {{ time_commitment or "не указано" }}
{% if additional_context %}
- Дополнительно: {{ additional_context }}
{% endif %}

Сгенерируй 4-6 конкретных микрошагов для достижения этой цели. Каждый шаг должен быть:
- Конкретным и действенным
- Реалистичным
- Измеримым

Верни JSON массив:
[
  {"title": "Шаг 1", "estimated_hours": 2.0},
  {"title": "Шаг 2", "estimated_hours": 5.0},
  ...
]
""")
