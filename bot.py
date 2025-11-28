import os
import io
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Audio
from pydub import AudioSegment

# OCR
from PIL import Image
import pytesseract

# AI
import openai

# DB
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


# ============================================================
# 🔧 CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY").encode()

openai.api_key = OPENROUTER_API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

# Mini App URL
WEBAPP_URL = "https://finai-app-v0.streamlit.app/"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ============================================================
# 📦 DATABASE
# ============================================================

Base = declarative_base()
engine = create_engine("sqlite:///database.db")
SessionLocal = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(String, unique=True)
    name = Column(String)

    transactions = relationship("Transaction", back_populates="user")
    categories = relationship("Category", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    amount = Column(Float)
    date = Column(Date)

    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


Base.metadata.create_all(engine)


# ============================================================
# 🧠 AI LOGIC: Intent + Entity Extraction
# ============================================================

async def ai_parse_text(prompt: str):
    """
    Вызывает OpenRouter LLM и получает JSON с intent/суммой/категорией/датой.
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="qwen/qwen-2-7b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — финансовый ассистент. Задача: извлечь данные о транзакциях.\n"
                        "Отвечай строго в JSON:\n"
                        "{intent: 'добавить_трату' | 'показать_аналитику' | 'дать_совет',\n"
                        " amount: число | null,\n"
                        " category: строка | null,\n"
                        " date: ISO8601 | null}\n"
                    )
                },
                {"role": "user", "content": prompt},
            ]
        )

        text = response["choices"][0]["message"]["content"]
        data = json.loads(text)
        return data

    except Exception as e:
        logging.error(f"AI error: {e}")
        return {"intent": "unknown"}


# ============================================================
# 🔊 AUDIO → TEXT
# ============================================================

def transcribe_voice(file_bytes: bytes) -> str:
    """
    Оффлайн транскрибация голосовых сообщений с помощью pydub + whisper.cpp (или любая локальная модель)
    Здесь для примера — просто заглушка.
    """
    # TODO: Вставить reallocal ASR
    return "голосовая транскрибация не настроена"


# ============================================================
# 🖼️ OCR
# ============================================================

def extract_text_from_image(img_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(img, lang="rus+eng")


# ============================================================
# 🗄️ SAVE TO DATABASE
# ============================================================

def add_transaction(tg_id: str, amount: float, category_name: str, date_str: str):
    session = SessionLocal()

    user = session.query(User).filter_by(tg_id=tg_id).first()
    if not user:
        return None

    # Ensure category exists
    category = session.query(Category).filter_by(user_id=user.id, name=category_name).first()
    if not category:
        category = Category(user_id=user.id, name=category_name)
        session.add(category)
        session.commit()

    dt = datetime.fromisoformat(date_str).date()

    tx = Transaction(
        user_id=user.id,
        category_id=category.id,
        amount=amount,
        date=dt
    )
    session.add(tx)
    session.commit()
    return tx


# ============================================================
# 🔘 MINI APP BUTTON
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton(
                text="Открыть финансовый ассистент",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ]

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nНажми кнопку ниже чтобы открыть Mini App.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# 📩 MAIN MESSAGE HANDLER
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    logging.info(f"[TEXT] {user.id}: {text}")

    data = await ai_parse_text(text)

    intent = data.get("intent")

    if intent == "добавить_трату":
        amount = data.get("amount")
        cat = data.get("category")
        dt = data.get("date", datetime.now().date().isoformat())

        tx = add_transaction(str(user.id), amount, cat, dt)

        if tx:
            await update.message.reply_text(
                f"🧾 Транзакция добавлена!\n"
                f"💸 {amount} ₽\n"
                f"📂 Категория: {cat}\n"
                f"📅 Дата: {tx.date}"
            )
        else:
            await update.message.reply_text("Ошибка при сохранении транзакции.")

    elif intent == "показать_аналитику":
        await update.message.reply_text("📊 Аналитика доступна в Mini App.\nОткрой через кнопку /start")

    elif intent == "дать_совет":
        # Второй вызов LLM для генерации совета
        advice = await ai_parse_text(f"Дай финансовый совет на основе запроса: {text}")
        await update.message.reply_text("💡 Совет:\n" + str(advice))

    else:
        await update.message.reply_text("Не понял запрос. Попробуйте уточнить.")


# ============================================================
# 🔉 VOICE HANDLER
# ============================================================

async def handle_voice(update: Update, context):
    user = update.effective_user

    file = await update.message.voice.get_file()
    file_bytes = await file.download_as_bytearray()

    text = transcribe_voice(file_bytes)
    await update.message.reply_text(f"🎤 Распознано: {text}")
    update.message.text = text

    return await handle_message(update, context)


# ============================================================
# 🖼️ PHOTO HANDLER
# ============================================================

async def handle_photo(update: Update, context):
    file = await update.message.photo[-1].get_file()
    file_bytes = await file.download_as_bytearray()
    text = extract_text_from_image(file_bytes)

    await update.message.reply_text(f"📷 Текст на изображении:\n{text}")
    update.message.text = text
    return await handle_message(update, context)


# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logging.info("Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
