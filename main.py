import os
from email_reader import fetch
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage


load_dotenv()
EM = os.getenv("EMAIL")
PASSWORD= os.getenv("PASSWORD")

def get_openrouter_chat() -> ChatOpenAI:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    API_URL = "https://openrouter.ai/api/v1"
    return ChatOpenAI(
        model="deepseek/deepseek-chat-v3-0324:free",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=API_URL,
        temperature=0.7,
        max_tokens=512,
    )

def query(prompt):
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content=prompt),
    ]
    chat = get_openrouter_chat()
    return chat.invoke(messages).content
threads = fetch(EM,PASSWORD)
print(query("Hello"))