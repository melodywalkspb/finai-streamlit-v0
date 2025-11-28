import hmac
import hashlib
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.filters import Command
from dotenv import load_dotenv
from database import create_user, add_transaction, get_transactions

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY").encode()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


def generate_signature(user_id: int) -> str:
    msg = str(user_id).encode()
    return hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()


@dp.message(Command(commands=["start"]))
async def start(msg: types.Message):
    user = msg.from_user
    create_user(user.id, user.first_name)

    signature = generate_signature(user.id)

    url = (
        "https://finai-app-v0.streamlit.app"
        f"?id={user.id}&sig={signature}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть Mini App", web_app=WebAppInfo(url=url))]
    ])

    await msg.answer("Открывай Mini App 👇", reply_markup=kb)


# Пример команды добавления транзакции через бот
@dp.message(Command(commands=["add"]))
async def add(msg: types.Message):
    parts = msg.text.split()
    if len(parts) != 3:
        await msg.answer("Используй: /add сумма категория")
        return

    _, amount_str, category = parts
    try:
        amount = float(amount_str)
    except:
        await msg.answer("Сумма должна быть числом")
        return

    tx = add_transaction(msg.from_user.id, amount, category)
    await msg.answer(f"Добавлена транзакция: {tx['amount']} ₽ в {tx['category']}")


async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
