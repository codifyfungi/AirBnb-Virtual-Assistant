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
CORS(app)

shutdown = False
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
        message_id INTEGER PRIMARY KEY,
        thread_id TEXT NOT NULL,
        content TEXT,
        name TEXT,
        host INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        message_id INTEGER
    )
    """)
    conn.commit()
    conn.close()
def handle_shutdown(_sig, _frame):
    global shutdown
    shutdown = True
signal.signal(signal.SIGTERM, handle_shutdown)
def get_last_seen_uid(cursor):
    cursor.execute("SELECT * FROM sync_state WHERE key='last_seen_uid'")
    row = cursor.fetchone()
    return (int(row[1]),int(row[2])) if row else (0,0)
def watch_inbox_loop():
    EM = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
<<<<<<< HEAD
    init_db()
    while not shutdown:    
=======
    while not shutdown:
>>>>>>> be6b14e701d4c6c305744e4dbe4e2a5992d4a491
        conn = sqlite3.connect("airbnb.db")
        cursor = conn.cursor()
        last_uid,last_message_id = get_last_seen_uid(cursor)
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EM, PASSWORD)
        mail.select("inbox")
        #Data is a list of byte strings
        status, data = mail.search(None,f'(UID {last_uid+1}:* FROM "express@airbnb.com")')
        if status == "OK":
            print("watch_inbox running")
            print(data)
        #Create list of ids corresponding to an email
        all_ids = b" ".join(data).split()
        #print(all_ids)
        for seq in all_ids:
            status, last_uid = mail.fetch(seq, '(UID)')
            last_uid = last_uid[0].decode().split()[2].rstrip(")")
            status, msg_data = mail.fetch(seq,"(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            # msg is your email.message.Message from msg_data[0][1]
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
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (last_message_id, thread_id, message, name, host))
                last_message_id += 1
            else:
                message = ptexts[2]
                host = image_srcs[2] == "https://a0.muscache.com/im/pictures/user/89a57bc6-3c38-435c-807d-904e2bac20c1.jpg?aki_policy=profile_medium" 
                name = ptexts[1]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (last_message_id, thread_id, message, name, host))
                last_message_id += 1 
            cursor.execute("""
                INSERT INTO sync_state (key, value, message_id)
                VALUES ('last_seen_uid', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, message_id = excluded.message_id
            """, (last_uid,last_message_id))
        conn.commit()
        conn.close()
        time.sleep(5)


@app.before_serving
def start_watch_inbox():
    init_db()
    threading.Thread(target=watch_inbox_loop, daemon=True).start()
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
        last_message_id = request.args.get("last_message_id", default=0, type=int)
        cursor.execute(
            """
            SELECT message_id, thread_id, content, name, host
            FROM messages
            WHERE message_id > ?
            ORDER BY thread_id, message_id
            """,
            (last_message_id,),
        )
        
        # Group messages by thread_id
        threads_data = defaultdict(list)
        thread_names = {}
        
        rows = cursor.fetchall()
        newest_id = last_message_id
        print("Get")
        print(last_message_id)
        for row in rows:
            message_id, thread_id, content, name, is_host = row
            if message_id > newest_id:
                newest_id = message_id
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
<<<<<<< HEAD
    threading.Thread(target=watch_inbox, daemon=True).start()
=======
>>>>>>> be6b14e701d4c6c305744e4dbe4e2a5992d4a491
    app.run(debug=True, use_reloader=False, port=5000)
