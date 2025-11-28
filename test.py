from pymongo import MongoClient
from urllib.parse import quote_plus

username = "melodywalkspb_db_user"
password = quote_plus("aqvyuTaopFWSnolJ")  # спецсимволы экранируются
uri = f"mongodb+srv://{username}:{password}@cluster0.2y7n9md.mongodb.net/?appName=Cluster0"

client = MongoClient(uri)

try:
    print(client.list_database_names())
    print("✅ Подключение успешно")
except Exception as e:
    print("❌ Ошибка подключения:", e)
