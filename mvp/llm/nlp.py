# mvp/llm/nlp.py
import os
import json
from datetime import datetime
import pytz
from openai import OpenAI

from mvp.llm.prompts import SYSTEM_PROMPT, SUMMARIZE_PROMPT
from mvp.config import OPENAI_API_KEY


class LLMBackend:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        tz_name = os.getenv("USER_TIMEZONE", "Europe/Moscow")
        try:
            self.tz = pytz.timezone(tz_name)
        except Exception:
            self.tz = pytz.UTC

    def _system_with_now(self) -> str:
        now = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        return SYSTEM_PROMPT + f'\n\nNOW="{now}"  # текущая дата/время пользователя\n'

    def parse_message(self, user_msg: str) -> dict:
        """Шаг 1: пользовательский текст → JSON интент (small_talk / event.search / event.mutate)"""
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self._system_with_now()},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)

    def summarize_response(self, core_result: dict) -> dict:
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SUMMARIZE_PROMPT},
                {"role": "user", "content": json.dumps(core_result, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)
