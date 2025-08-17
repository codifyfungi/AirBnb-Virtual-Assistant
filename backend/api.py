from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3

from collections import defaultdict
from langchain_core.messages import trim_messages
from dotenv import load_dotenv
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
load_dotenv()

app = Flask(__name__)
CORS(app)

EM = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
with open("context.txt", "r", encoding="latin-1") as f:
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
    """Get all email threads with messages from database"""
    try:
        # Connect to database
        conn = sqlite3.connect("airbnb.db")
        cursor = conn.cursor()
        
        # Get all messages grouped by thread_id
        cursor.execute("""
            SELECT message_id, thread_id, content, name, host
            FROM messages 
            ORDER BY thread_id, message_id
        """)
        
        # Group messages by thread_id
        threads_data = defaultdict(list)
        thread_names = {}
        
        for row in cursor.fetchall():
            message_id, thread_id, content, name, is_host = row
            # Initialize thread if not exists
            # Store first guest name as thread name
            if not is_host:
                thread_names[thread_id] = name
            
            # Format message for API response
            message_data = {
                "role": "host" if is_host else "guest",
                "text": content,
                "name": name,
                "time": "Recent"
            }
            
            threads_data[thread_id].append(message_data)
        conn.close()
        
        return jsonify({
            "threads": thread_names,
            "messages": threads_data
        })
        
    except Exception as e:
        print(f"Error fetching threads from database: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process a prompt for a specific thread"""
    try:
        data = request.json
        messages = data.get('messages', [])
        
        # Generate AI response using the query function
        response = query(messages, context)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
