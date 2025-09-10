import os
import json
from openai import OpenAI
from .prompts import SYSTEM_PROMPT
from .router import handle_intent


class LLMBackend:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY не найден. Проверь .env")

        self.client = OpenAI(api_key=api_key)

    def llm_query(self, user_msg: str) -> str:
        """Запрос к OpenAI Chat API"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",   # можно заменить на gpt-4o или gpt-3.5
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    def handle_message(self, user_msg: str):
        """Главная точка входа: отвечает small talk или запускает действие"""
        msg = self.llm_query(user_msg)

        try:
            parsed = json.loads(msg)
            return handle_intent(parsed)
        except Exception:
            return msg
