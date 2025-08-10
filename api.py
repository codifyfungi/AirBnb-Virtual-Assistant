from flask import Flask, jsonify, request
from flask_cors import CORS
import os

from langchain_core.messages import trim_messages
from email_reader import fetch
from dotenv import load_dotenv
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
load_dotenv()

app = Flask(__name__)
CORS(app)

EM = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
with open("CheckInInstructions.txt", "r", encoding="latin-1") as f:
    context = f.read()
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

def query(messages, context):
    tMessages = [SystemMessage(content=f"You are the host of an Oceanside house, your name is Tina Han. Be warm, concise, and solution-oriented. Never share internal notes. Follow HOUSE RULES and AIRBNB POLICIES below.\n\n{context}")]
    for m in messages:
        if m.get('role') == "host":
            tMessages.append(AIMessage(content=f"{m.get('name')} {m.get('text', '')}"))
        else:
            tMessages.append(HumanMessage(content=f"{m.get('name')} {m.get('text', '')}"))
    print("Messages being sent to AI:", tMessages)
    chat = get_openrouter_chat()
    return chat.invoke(tMessages).content
with open("CheckInInstructions.txt", "r", encoding="latin-1") as f:
    context = f.read()
@app.route('/api/threads', methods=['GET'])
def get_threads():
    """Get all email threads with messages"""
    try:
        # Fetch email threads using your existing function
        (thread_name,email_threads) = fetch(EM, PASSWORD)
    
        
        return jsonify({
            "threads": thread_name,
            "messages": email_threads
        })
        
    except Exception as e:
        print(f"Error fetching threads: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process a prompt for a specific thread"""
    try:
        data = request.json
        thread_id = data.get('threadId')
        messages = data.get('messages', [])
        
        # Generate AI response using the query function
        response = query(messages, context)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
