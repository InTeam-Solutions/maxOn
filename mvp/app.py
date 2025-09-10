import os
import logging
from dotenv import load_dotenv
from ai_backend.nlp import LLMBackend


# --- ЛОГГИРОВАНИЕ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- ЗАГРУЗКА .env ---
dotenv_path = "/Users/asgatakmaev/Desktop/business/Initio/mvp/.env"
load_dotenv(dotenv_path)

logger.info(f".env загружен из: {dotenv_path}")

# Логируем безопасно
for key, value in os.environ.items():
    if "KEY" in key or "SECRET" in key:
        logger.info(f"{key}=*** скрыт ***")


# --- ОСНОВНОЙ ЦИКЛ ---
def main():
    llm = LLMBackend()
    logger.info("LLMBackend инициализирован (OpenAI)")

    print("Ассистент запущен. Пиши сообщения (выход = quit).")
    while True:
        user_msg = input("Ты: ")
        if user_msg.lower() in ["quit", "exit", "выход"]:
            break
        response = llm.handle_message(user_msg)
        print("Бот:", response)


if __name__ == "__main__":
    main()
