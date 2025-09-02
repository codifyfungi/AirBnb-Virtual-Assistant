from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import time
import imaplib
import email
import re
import signal
import threading
from bs4 import BeautifulSoup

from collections import defaultdict
from langchain_core.messages import trim_messages
from dotenv import load_dotenv
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://bnbot.netlify.app","http://localhost:5173"], supports_credentials=True)
lock = threading.Lock()
with open("context.txt", "r", encoding="latin-1") as f:
    context = f.read()
def init_db():
    conn = sqlite3.connect("airbnb.db")
    cursor = conn.cursor()

    # Create table for clients
    # Create table for messages
    # message id is email uid
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        uid INTEGER PRIMARY KEY,
        thread_id TEXT NOT NULL,
        content TEXT,
        name TEXT,
        host INTEGER
    )
    """)
    conn.commit()
    conn.close()
def get_last_seen_uid(cursor):
    cursor.execute("SELECT MAX(uid) FROM messages")
    row = cursor.fetchone()
    return row[0] if row[0] is not None else 0
@app.route('/api/watch-inbox', methods=['POST'])
def watch_inbox():
    if not lock.acquire(blocking=False):
        print("Already in USE")
        return ("", 204)
    try:
        init_db()
        EM = os.getenv("EMAIL")
        PASSWORD = os.getenv("PASSWORD")
        conn = sqlite3.connect("airbnb.db")
        cursor = conn.cursor()
        last_uid = get_last_seen_uid(cursor)
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EM, PASSWORD)
        mail.select("inbox")
        #Data is a list of byte strings
        status, data = mail.uid("search", None, f'UID {last_uid+1}:* FROM "express@airbnb.com"')
        if status == "OK":
            print("watch_inbox running")
            print(data)
        #Create list of ids corresponding to an email
        all_ids = b" ".join(data).split()
        print("IDS")
        print(last_uid+1)
        for uid in all_ids:
            status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
            print(uid)
            uid = int(uid.decode())
            print(uid)
            msg = email.message_from_bytes(msg_data[0][1])
            # msg is your email.message.Message from msg_data[0][1]
            print(msg["From"])
            plain_body = ""
            html_body  = ""

            if msg.is_multipart():
                for part in msg.walk():
                    # skip containers and attachments
                    if part.get_content_maintype() == "multipart" or part.get("Content-Disposition"):
                        continue

                    ctype   = part.get_content_type()
                    charset = part.get_content_charset() or "utf-8"
                    if ctype == "text/plain":
                        # direct concatenation
                        plain_body += part.get_payload(decode=False) + "\n"
                    elif ctype == "text/html":
                        html_body += part.get_payload(decode=True).decode(charset, "replace") + "\n"
            else:
                # single‑part message
                ctype   = msg.get_content_type()
                charset = msg.get_content_charset() or "utf-8"
                if ctype == "text/plain":
                    plain_body = msg.get_payload(decode=False)
                elif ctype == "text/html":
                    html_body = msg.get_payload(decode=True).decode(charset, "replace")
            soup = BeautifulSoup(html_body, "html.parser")
            ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            h2texts = [h2.get_text(" ", strip=True) for h2 in soup.find_all("h2")]
            image_srcs = [img["src"] for img in soup.find_all("img", src=True)]
            #Retrieve message thread id
            m = re.search(
                r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
                plain_body
            )
            thread_id = m.group(1)
            #Find the message content
            m = re.search(
                r"\[https://www\.airbnb\.com/help/article/209\?[^]]+\]"
                r"\s*(?:=\r?\n)?\.?\s*(?:\r?\n)+"
                #Non-Greedy, match as little as you can while matching the pattern
                r"(.*?)"
                r"(?=\s*(?:Reply|Review inquiry)\b)",
                plain_body,
                flags=re.DOTALL
            )
            #print(plain_body)
            #if m:
            #    message = m.group(1)
            #m = re.search(r"89a57bc6-3c38-435c-807d-904e2bac20c1",html_body)
            if ptexts[1] == "Host" or ptexts[1] == "Guest" or ptexts[1] == "Booker":
                message = ptexts[2]
                host = ptexts[1] == "Host"
                name = h2texts[0]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, thread_id, message, name, host))
            else:
                message = ptexts[2]
                host = image_srcs[2] == "https://a0.muscache.com/im/pictures/user/89a57bc6-3c38-435c-807d-904e2bac20c1.jpg?aki_policy=profile_medium" 
                name = ptexts[1]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, thread_id, message, name, host))
        conn.commit()
        conn.close()
        return ("", 204)
    finally:
        lock.release()
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
@app.route('/api/threads', methods=['GET'])
def get_threads():
    """Get all email threads with messages from database"""
    try:
        # Connect to database
        conn = sqlite3.connect("airbnb.db")
        cursor = conn.cursor()
        
        # Get only messages newer than the provided last_message_id
        last_uid = request.args.get("last_message_id", default=0, type=int)
        cursor.execute(
            """
            SELECT uid, thread_id, content, name, host
            FROM messages
            WHERE uid > ?
            ORDER BY uid
            LIMIT 100
            """,
            (last_uid,),
        )
        rows = cursor.fetchall()  # To maintain chronological order for display
        
        # Group messages by thread_id
        threads_data = defaultdict(list)
        thread_names = {}
        
        rows = cursor.fetchall()
        newest_id = last_uid
        print("Get")
        print(last_uid)
        for row in rows:
            uid, thread_id, content, name, is_host = row
            if uid > newest_id:
                newest_id = uid
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
            "messages": threads_data,
            "last_message_id": newest_id,
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
    app.run(debug=True, use_reloader=False, port=5000)
