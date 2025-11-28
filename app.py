import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Telegram User Test", layout="wide")

st.title("Telegram Mini App — User Debug")

# -------------------------------
# Inject JS to extract Telegram WebApp user data
# -------------------------------
components.html("""
<script>
    document.addEventListener("DOMContentLoaded", function() {
        try {
            const tg = window.Telegram.WebApp;
            tg.expand();

            const user = tg.initDataUnsafe?.user;

            if (user) {
                const params = new URLSearchParams(window.location.search);
                params.set("user", JSON.stringify(user));
                const newUrl = window.location.pathname + '?' + params.toString();
                window.history.replaceState(null, "", newUrl);
            } else {
                console.log("User object not available");
            }
        } catch (e) {
            console.log("Telegram WebApp not available:", e);
        }
    });
</script>
""", height=0)

# -------------------------------
# Read user from query params
# -------------------------------
params = st.query_params
user_json = params.get("user")

if not user_json:
    st.error("⚠ Нет данных Telegram WebApp. Mini App должен быть открыт через Telegram.")
    st.stop()

try:
    user = json.loads(user_json)
except:
    st.error("Ошибка обработки Telegram user JSON.")
    st.stop()

# -------------------------------
# Output user data
# -------------------------------
st.subheader("Полученные данные пользователя Telegram:")
st.json(user)

st.write(f"**ID:** {user.get('id')}")
st.write(f"**Имя:** {user.get('first_name')}")
st.write(f"**Фамилия:** {user.get('last_name')}")
st.write(f"**Юзернейм:** @{user.get('username')}")
st.write(f"**Язык:** {user.get('language_code')}")
