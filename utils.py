# utils.py
import os
import hmac
import hashlib
import base64
from typing import Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import pytesseract
from PIL import Image
import io
import soundfile as sf
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except Exception:
    VOSK_AVAILABLE = False

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "./models/vosk-small-ru")

def verify_telegram_init_data(init_data: str) -> Dict[str, Any]:
    """
    Verify Telegram WebApp initData or login widget.
    init_data: raw query string: "id=...&auth_date=...&hash=..."
    Returns dict of fields if valid, raises ValueError if not.
    """
    # Parse
    data = {}
    for part in init_data.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            data[k] = v
    # create data_check_string
    hash_provided = data.get("hash")
    if not hash_provided:
        raise ValueError("No hash in init_data")
    check_list = []
    for k in sorted([k for k in data.keys() if k != "hash"]):
        check_list.append(f"{k}={data[k]}")
    data_check_string = "\n".join(check_list)
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if computed_hash != hash_provided:
        raise ValueError("Invalid init data signature")
    return data

# OCR for images (pytesseract)
def ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang='rus+eng')
        return text
    except Exception as e:
        return ""

# Offline transcription using Vosk (wav bytes)
def transcribe_audio_bytes(audio_bytes: bytes, sample_rate=16000) -> str:
    if not VOSK_AVAILABLE:
        return ""
    # Ensure model loaded
    model = Model(VOSK_MODEL_PATH)
    rec = KaldiRecognizer(model, sample_rate)
    # read file samples
    import wave, tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        wf = wave.open(tmp.name, "rb")
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                results.append(rec.Result())
        results.append(rec.FinalResult())
        # aggregate
        import json
        texts = []
        for r in results:
            try:
                jr = json.loads(r)
                if 'text' in jr:
                    texts.append(jr['text'])
            except:
                continue
        return " ".join(texts)

# helper: safe parse float
def safe_float(v):
    try:
        return float(str(v).replace(",", "."))
    except:
        return None
