import os
import requests
from email_reader import fetch
from dotenv import load_dotenv


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

EM = os.getenv("EMAIL")
PASSWORD= os.getenv("PASSWORD")

def query(prompt):
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512
    }
    resp = requests.post(url=API_URL, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
threads = fetch(EM,PASSWORD)
print(query("Hello"))