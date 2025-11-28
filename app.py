import os
import json
import streamlit as st
from datetime import datetime, date
from dotenv import load_dotenv

# Database
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Pages
from streamlit_option_menu import option_menu
import plotly.express as px


# Load env variables
load_dotenv()

# Telegram config
TG_BOT_NAME = os.getenv("TG_BOT_NAME")

# DB setup
Base = declarative_base()
engine = create_engine("sqlite:///database.db")
SessionLocal = sessionmaker(bind=engine)


# -------------------------------------------------------------------------
# 🗄️ MODELS
# -------------------------------------------------------------------------
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


# -------------------------------------------------------------------------
# 🔐 AUTH — Telegram Mini App Login
# -------------------------------------------------------------------------
def authenticate_user():
    """
    Считывает данные Telegram WebApp из query params.
    Mini App внутри Telegram передаёт user={...}
    """
    params = st.query_params

    if "user" not in params:
        st.error("⚠ Авторизация не выполнена. Mini App должен запускаться через Telegram.")
        st.stop()

    try:
        tg_user_raw = params.get("user")
        tg_user = json.loads(tg_user_raw)

        tg_id = str(tg_user["id"])
        full_name = tg_user.get("first_name", "") + " " + tg_user.get("last_name", "")

        return tg_id, full_name

    except Exception as e:
        st.error(f"Ошибка авторизации Telegram: {e}")
        st.stop()


# -------------------------------------------------------------------------
# 🎨 CUSTOM CSS — Telegram-style UI
# -------------------------------------------------------------------------
def apply_css():
    st.markdown(
        """
        <style>
        body, .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
            font-family: "Segoe UI", sans-serif;
        }

        /* Light Theme */
        :root {
            --background-color: #ffffff;
            --text-color: #222;
            --card-bg: #f3f3f3;
        }

        /* Dark Theme */
        .dark-theme {
            --background-color: #0e1621;
            --text-color: #e9eef4;
            --card-bg: #1c2733;
        }

        .telegram-card {
            background: var(--card-bg);
            padding: 16px;
            border-radius: 12px;
            margin-top: 10px;
        }

        /* Bottom menu */
        .bottom-menu {
            position: fixed;
            bottom: 0;
            left: 0; right: 0;
            height: 60px;
            background: var(--card-bg);
            display: flex;
            justify-content: space-around;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------------
# 📄 PAGE: TRANSACTIONS
# -------------------------------------------------------------------------
def page_transactions(user_id):
    st.header("💰 История транзакций")

    session = SessionLocal()

    categories = {c.id: c.name for c in session.query(Category).filter_by(user_id=user_id)}
    transactions = session.query(Transaction).filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()

    if st.button("➕ Добавить транзакцию"):
        with st.form("add_tx"):
            amount = st.number_input("Сумма", step=0.01)
            category_name = st.selectbox("Категория", list(categories.values()))
            date_value = st.date_input("Дата", date.today())
            submitted = st.form_submit_button("Добавить")

            if submitted:
                category_id = [cid for cid, name in categories.items() if name == category_name][0]

                tx = Transaction(
                    user_id=user_id,
                    category_id=category_id,
                    amount=amount,
                    date=date_value
                )
                session.add(tx)
                session.commit()
                st.success("Транзакция добавлена!")
                st.experimental_rerun()

    # List
    for tx in transactions:
        with st.container():
            st.markdown(f"""
                <div class="telegram-card">
                    <b>{categories.get(tx.category_id)}</b><br>
                    {tx.amount} ₽ — {tx.date.strftime('%d.%m.%Y')} 
                </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            if col1.button(f"✏ Редактировать {tx.id}"):
                with st.form(f"edit-{tx.id}"):
                    new_amount = st.number_input("Сумма", value=tx.amount)
                    new_date = st.date_input("Дата", value=tx.date)
                    new_cat = st.selectbox("Категория", list(categories.values()))
                    submit_edit = st.form_submit_button("Сохранить")

                    if submit_edit:
                        tx.amount = new_amount
                        tx.date = new_date
                        tx.category_id = [cid for cid, name in categories.items() if name == new_cat][0]
                        session.commit()
                        st.success("Изменено!")
                        st.experimental_rerun()

            if col2.button(f"🗑 Удалить {tx.id}"):
                session.delete(tx)
                session.commit()
                st.experimental_rerun()


# -------------------------------------------------------------------------
# 📄 PAGE: CATEGORIES
# -------------------------------------------------------------------------
def page_categories(user_id):
    st.header("📂 Категории")

    session = SessionLocal()
    categories = session.query(Category).filter_by(user_id=user_id).all()

    for c in categories:
        with st.container():
            st.markdown(
                f"<div class='telegram-card'>{c.name}</div>",
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)

            if col1.button(f"✏ Редактировать {c.id}"):
                new_name = st.text_input("Новое название", value=c.name, key=f"name_{c.id}")
                if st.button(f"Сохранить {c.id}"):
                    c.name = new_name
                    session.commit()
                    st.experimental_rerun()

            if col2.button(f"🗑 Удалить {c.id}"):
                session.delete(c)
                session.commit()
                st.experimental_rerun()

    st.subheader("Добавить категорию")
    with st.form("add_cat"):
        name = st.text_input("Название")
        submitted = st.form_submit_button("Добавить")

        if submitted:
            c = Category(user_id=user_id, name=name)
            session.add(c)
            session.commit()
            st.experimental_rerun()


# -------------------------------------------------------------------------
# 📄 PAGE: PROFILE
# -------------------------------------------------------------------------
def page_profile(tg_id, full_name):
    st.header("👤 Профиль")

    st.markdown(
        f"""
        <div class="telegram-card">
            <b>Telegram ID:</b> {tg_id} <br>
            <b>Имя:</b> {full_name}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------------
# 🎬 MAIN APP
# -------------------------------------------------------------------------
def main():
    apply_css()

    # ВСТАВЬ ЭТО САМЫМ ПЕРВЫМ
    st.markdown("""
        <script>
        if (window.Telegram && window.Telegram.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.expand();
        
            const user = tg.initDataUnsafe?.user;
            if (user) {
                const params = new URLSearchParams(window.location.search);
                params.set("user", JSON.stringify(user));
        
                const newUrl = window.location.pathname + '?' + params.toString();
                window.history.replaceState(null, "", newUrl);
            }
        }
        </script>
    """, unsafe_allow_html=True)

    st.markdown("## 🧠 Личный финансовый AI-ассистент")

    tg_id, full_name = authenticate_user()

    # Ensure user exists
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=tg_id).first()

    if not user:
        user = User(tg_id=tg_id, name=full_name)
        session.add(user)
        session.commit()

    # Bottom menu
    selected = option_menu(
        None,
        ["Транзакции", "Категории", "Профиль"],
        icons=["cash-stack", "list-ul", "person"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )

    if selected == "Транзакции":
        page_transactions(user.id)
    elif selected == "Категории":
        page_categories(user.id)
    elif selected == "Профиль":
        page_profile(tg_id, full_name)


if __name__ == "__main__":
    main()

