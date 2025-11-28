from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["finance_app"]
users_col = db["users"]


# -------------------------------
# Пользователь
# -------------------------------
def get_user(tg_id: int):
    return users_col.find_one({"tg_id": tg_id})


def create_user(tg_id: int, name: str = "Unknown"):
    user = get_user(tg_id)
    if user:
        return user
    user_doc = {
        "tg_id": tg_id,
        "name": name,
        "categories": [],
        "transactions": []
    }
    users_col.insert_one(user_doc)
    return user_doc


# -------------------------------
# Категории
# -------------------------------
def add_category(tg_id: int, name: str):
    user = create_user(tg_id)
    if name in [c["name"] for c in user["categories"]]:
        return None  # уже есть
    users_col.update_one(
        {"tg_id": tg_id},
        {"$push": {"categories": {"_id": ObjectId(), "name": name}}}
    )
    return name


def get_categories(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return []
    return user.get("categories", [])


# -------------------------------
# Транзакции
# -------------------------------
def add_transaction(tg_id: int, amount: float, category: str, date: str = None):
    user = create_user(tg_id)
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    tx = {
        "_id": ObjectId(),
        "amount": amount,
        "category": category,
        "date": date
    }
    users_col.update_one(
        {"tg_id": tg_id},
        {"$push": {"transactions": tx}}
    )
    return tx


def get_transactions(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return []
    return user.get("transactions", [])
