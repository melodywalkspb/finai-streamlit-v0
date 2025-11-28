import streamlit as st
import hashlib
import hmac
import os
from dotenv import load_dotenv

st.set_page_config(page_title="Secure Mini App", layout="wide")

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY").encode()
st.write(f"SECRET_KEY: {SECRET_KEY}")
st.write(f"STREAMLIT_SERVER_PORT: {STREAMLIT_SERVER_PORT}")

st.title("🔐 Secure Telegram Mini App") 


def verify_signature(user_id: str, signature: str) -> bool:
    """
    Проверяем подпись HMAC, созданную ботом.
    """
    expected_sig = hmac.new(
        SECRET_KEY, user_id.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature)


# -------------------------------
# 1. Получаем параметры из URL
# -------------------------------
params = st.query_params
user_id = params.get("id")
signature = params.get("sig")

st.write(f"SK: {user_id}")
st.write(f"SK: {signature}")

if not user_id or not signature:
    st.error("❌ Нет данных. Открой Mini App через Telegram бота.")
    st.stop()

# -------------------------------
# 2. Проверяем подпись
# -------------------------------
if not verify_signature(user_id, signature):
    st.error("⛔ Подпись недействительна! Доступ запрещён.")
    st.stop()

# -------------------------------
# 3. Выводим данные
# -------------------------------
st.success("✔ Доступ разрешён")

st.write("### 👤 Telegram User")
st.write(f"**User ID:** `{user_id}`")



