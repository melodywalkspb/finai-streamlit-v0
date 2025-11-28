import streamlit as st
import os
import hmac
import hashlib
from dotenv import load_dotenv
from database import get_user, get_transactions, get_categories

st.set_page_config(page_title="Secure Mini App", layout="wide")
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY").encode()

st.title("💰 Финансовый ассистент (Mini App)")

# -------------------------------
# Получаем параметры из URL
# -------------------------------
params = st.experimental_get_query_params()
user_id = params.get("id", [None])[0]
sig = params.get("sig", [None])[0]

if not user_id or not sig:
    st.error("Открой Mini App через Telegram бота")
    st.stop()

# -------------------------------
# Проверка подписи HMAC
# -------------------------------
expected_sig = hmac.new(SECRET_KEY, str(user_id).encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected_sig, sig):
    st.error("Подпись недействительна! Доступ запрещён.")
    st.stop()

user_id = int(user_id)
user = get_user(user_id)
st.success(f"Привет, {user['name']}! Доступ разрешён ✅")

# -------------------------------
# Показ категорий
# -------------------------------
st.subheader("Категории")
cats = get_categories(user_id)
st.write([c["name"] for c in cats])

# -------------------------------
# Показ транзакций
# -------------------------------
st.subheader("Транзакции")
txs = get_transactions(user_id)
for tx in txs:
    st.write(f"{tx['date']} — {tx['category']} — {tx['amount']} ₽")
