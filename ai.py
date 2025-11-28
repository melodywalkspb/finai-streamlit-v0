# ai.py
import os
import re
import json
import requests
from dotenv import load_dotenv
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://api.openrouter.ai/v1/chat/completions")
# if using official openai client: you can adapt to OpenRouter-compatible endpoint

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

# --- Basic LLM wrapper for OpenRouter ---
class OpenRouterClient:
    def __init__(self, api_url=OPENROUTER_API_URL, api_key=OPENROUTER_API_KEY, model="gpt-4o-mini"):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list, max_tokens=512, temperature=0.2) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Adjust extraction depending on API response shape
        # Some OpenRouter responses follow openai-like structure:
        text = ""
        if "choices" in data and len(data["choices"]) > 0:
            text = data["choices"][0]["message"].get("content", "")
        else:
            text = json.dumps(data)
        return text

# --- Intent recognition via regex + LLM fallback ---
INTENT_PATTERNS = {
    "добавить_трату": [
        r"\b(потратил|потратила|купил|заплатил|оплатил|пополнить|добавь|запиши)\b",
    ],
    "показать_аналитику": [
        r"\b(сколько|покажи|показать|итог|статистика|анализ|посчитать)\b",
    ],
    "дать_совет": [
        r"\b(совет|подскажи|как экономить|рекомендации|что посоветуешь)\b",
    ]
}

def regex_intent(text: str) -> Optional[str]:
    t = text.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for p in patterns:
            if re.search(p, t):
                return intent
    return None

# --- Entity extraction: amount, category, date, note ---
CURRENCY_RE = r"(?P<amount>\d+(?:[.,]\d{1,2})?)\s*(?:₽|rub|руб|rubles|eur|€|\$|usd)?"
CATEGORY_KEYWORDS = {
    "еда": ["еда", "обед", "ужин", "кофе", "ресторан", "кафе", "завтрак", "перекус"],
    "transport": ["транспорт", "такси", "uber", "bolt", "метро", "автобус"],
    "shopping": ["магазин", "шопинг", "кофта", "телефон"],
    "health": ["аптека", "медицина", "врач"],
    "income": ["зарплата", "доход", "прибыль"],
    "others": []
}

DAY_KEYWORDS = {
    "вчера": -1,
    "сегодня": 0,
    "позавчера": -2,
    "завтра": 1
}

def extract_amount(text: str) -> Optional[float]:
    m = re.search(CURRENCY_RE, text.replace(",", "."))
    if m:
        try:
            return float(m.group("amount"))
        except:
            return None
    return None

def extract_date(text: str, ref: datetime = None) -> Optional[datetime]:
    ref = ref or datetime.now()
    t = text.lower()
    for k, off in DAY_KEYWORDS.items():
        if k in t:
            return (ref + timedelta(days=off)).replace(hour=12, minute=0, second=0, microsecond=0)
    # try dateutil
    try:
        d = dateparser.parse(text, fuzzy=True, default=ref)
        return d
    except Exception:
        return None

def extract_category(text: str) -> str:
    t = text.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        for k in keys:
            if k in t:
                return cat
    # fallback: try to grab noun after 'на' or 'для'
    m = re.search(r"(?:на|для)\s+([а-яa-zA-Z\-]+)", t)
    if m:
        return m.group(1)
    return "others"

def extract_entities(text: str) -> Dict[str, Any]:
    amount = extract_amount(text)
    date = extract_date(text)
    category = extract_category(text)
    # note: remove amount and date tokens to get note
    note = text
    if amount is not None:
        note = re.sub(CURRENCY_RE, "", note, flags=re.IGNORECASE)
    # remove date words heuristically
    for k in DAY_KEYWORDS.keys():
        note = note.replace(k, "")
    return {
        "amount": amount,
        "category": category,
        "date": date,
        "note": note.strip()
    }

# --- Prompt templates ---
PROMPT_TEMPLATES = {
    "добавить_трату": (
        "Ты — ассистент для управления личными финансами. "
        "Пользователь говорит: \"{text}\". "
        "Извлеки в формате JSON: intent (добавить_трату), amount (число, если есть), category (строка), date (ISO8601 или null), note (строка). "
        "Если не уверен о категории, угадай её кратко. Ответ строго в JSON."
    ),
    "показать_аналитику": (
        "Ты — финансовый ассистент. Пользователь просит: \"{text}\". "
        "Верни JSON с intent: показать_аналитику, period: (last_7_days|last_30_days|this_month|custom), category (если есть) и краткое объяснение."
    ),
    "дать_совет": (
        "Ты — финансовый аналитик. Пользователь просит совет: \"{text}\". "
        "Проанализируй последние 30 операций (вставь их в контекст, если есть) и дай 3 конкретных совета по экономии в формате JSON."
    )
}

def ai_extract_with_llm(text: str, client: Optional[OpenRouterClient] = None, intent: Optional[str] = None) -> Dict[str, Any]:
    """
    Используется, если regex-intent не дал результата или для уточнения сущностей.
    Возвращает dict с полями intent, amount, category, date, note.
    """
    client = client or OpenRouterClient()
    if not intent:
        intent = "добавить_трату"
    prompt = PROMPT_TEMPLATES.get(intent, PROMPT_TEMPLATES["добавить_трату"]).format(text=text)
    messages = [{"role":"system","content":"You are a JSON-output assistant for finance parsing."},
                {"role":"user","content":prompt}]
    try:
        raw = client.chat(messages, max_tokens=300)
        # try parse JSON from raw text
        j = None
        try:
            jpos = raw.find("{")
            if jpos != -1:
                jtext = raw[jpos:]
                j = json.loads(jtext)
        except Exception:
            # last fallback — return best-effort using regex extractor
            j = {
                "intent": intent,
                "amount": extract_amount(text),
                "category": extract_category(text),
                "date": extract_date(text).isoformat() if extract_date(text) else None,
                "note": text
            }
        if j:
            # normalize
            return {
                "intent": j.get("intent", intent),
                "amount": float(j.get("amount")) if j.get("amount") else extract_amount(text),
                "category": j.get("category") or extract_category(text),
                "date": dateparser.parse(j["date"]) if j.get("date") else extract_date(text),
                "note": j.get("note", text)
            }
    except Exception as e:
        # LLM errors — fallback
        return {
            "intent": intent,
            "amount": extract_amount(text),
            "category": extract_category(text),
            "date": extract_date(text),
            "note": text
        }
