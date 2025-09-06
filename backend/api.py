from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import imaplib
import email
import re
import threading
from bs4 import BeautifulSoup

from collections import defaultdict
import chromadb
from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction
from langchain_core.messages import trim_messages
from dotenv import load_dotenv
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["https://bnbot.netlify.app", "http://localhost:5173"]}})
lock = threading.Lock()
"""
Set up vector DB for rule retrieval using a free HuggingFace model.
"""
vect_client = chromadb.PersistentClient(path="vector_db")
embed_fn = HuggingFaceEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
vect_collection = vect_client.get_or_create_collection(
    "instructions",
    embedding_function=embed_fn
)
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
def get_body(msg):
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
        m = re.search(
            r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
            plain_body
        ) 
    return plain_body, html_body
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
        # Retrieve any new automated reservation reminders
        status, data = mail.uid(
            "search", None,
            'UID', f'{last_uid+1}:*',
            'FROM', '"automated@airbnb.com"',
            'SUBJECT', '"Reservation Reminder"'
        )
        auto_ids = b" ".join(data).split()
        #Create list of ids corresponding to an email    
        status, data = mail.uid(
            "search", None,
            'UID', f'{last_uid+1}:*',
            'FROM', '"express@airbnb.com"'
        )
        express_ids = b" ".join(data).split()
        print("IDS")
        print(last_uid+1)
        for uid in auto_ids:
            status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
            uid = int(uid.decode())
            print(uid)
            msg = email.message_from_bytes(msg_data[0][1])
            plain_body, html_body = get_body(msg)
            m = re.search(
                r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
                plain_body
            )
            reservation_id = m.group(1)
            list_m = re.search(r"https?://www\.airbnb\.com/rooms/(\d+)", plain_body)
            listing_id = list_m.group(1) if list_m else None
            loc_m = re.search(
                r"https?://www\.airbnb\.com/hosting/reservations/details/[^\s]+\S.*?\r?\n\s*([A-Za-z ]+,\s*[A-Z]{2}|US)\s*(?:\r?\n|$)",
                plain_body,
                flags=re.IGNORECASE | re.DOTALL
            )
            guest_location = loc_m.group(1).strip() if loc_m else None
            # Extract guest name from Subject line (e.g. 'Reservation reminder: Jerome is coming soon!')
            subject = msg.get('Subject', '')
            # Capture the name following 'Reservation reminder:'
            sub_m = re.search(r'Reservation reminder:\s*([A-Za-z]+)', subject, flags=re.IGNORECASE)
            guest_name = sub_m.group(1) if sub_m else None
            # Extract number of adults and children
            ad_m = re.search(r"(\d+)\s+adults", plain_body)
            adults = int(ad_m.group(1)) if ad_m else None
            ch_m = re.search(r"(\d+)\s+children", plain_body)
            children = int(ch_m.group(1)) if ch_m else None
            # Extract payment details
            paid_m = re.search(r"TOTAL \(USD\)\s*\$([\d,\.]+)", plain_body)
            total_paid = paid_m.group(1) if paid_m else None
            earn_m = re.search(r"YOU EARN\s*\$([\d,\.\-]+)", plain_body)
            host_payout = earn_m.group(1) if earn_m else None
            # Extract check-in and check-out dates based on the block with 'Check-in    Checkout' and a date line
            dates_m = re.search(
                r'Check-in[\s\S]*?^\s*([A-Za-z]{3},\s*[A-Za-z]{3}\s+\d{1,2}(?:,\s*\d{4})?)\s+([A-Za-z]{3},\s*[A-Za-z]{3}\s+\d{1,2}(?:,\s*\d{4})?)',
                plain_body,
                flags=re.IGNORECASE | re.MULTILINE
            )
            if dates_m:
                check_in_date, check_out_date = dates_m.groups()
            else:
                check_in_date = check_out_date = None
            # Override with direct muscache user image URL from either /im/pictures/user or /im/users/.../profile_pic
            img_m = re.search(
                # Match both /im/pictures/user and /im/users/.../profile_pic paths
                r'(https://a0\.muscache\.com/im/(?:pictures/user|users/[^/\s<>]+/profile_pic)/[^"\s<>]+\.(?:jpe?g)(?:\?[^"\s<>]*)?)',
                html_body,
                flags=re.IGNORECASE
            )
            try:
                guest_image = img_m.group(1)
            except AttributeError:
                guest_image = None
            soup = BeautifulSoup(html_body, "html.parser")
            ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            message = None
            if listing_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO listings (listing_id) VALUES (?)",
                    (listing_id,)
                )
            # Upsert reservation with detailed fields
            cursor.execute(
                "INSERT OR IGNORE INTO reservations (reservation_id, listing_id, guest_name, guest_image, guest_location, adults, children, guest_paid, host_payout, check_in_date, check_out_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (reservation_id, listing_id, guest_name, guest_image, guest_location, adults, children, total_paid, host_payout, check_in_date, check_out_date)
            )
            if ptexts[5] != "Entire home/apt":
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, ptexts[5], guest_name, 0))
        for uid in express_ids:
            status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
            uid = int(uid.decode())
            msg = email.message_from_bytes(msg_data[0][1])
            print(uid)
            print(msg["From"])
            plain_body, html_body = get_body(msg)
            m = re.search(
                r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
                plain_body
            )
            reservation_id = m.group(1)
            soup = BeautifulSoup(html_body, "html.parser")
            ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            h2texts = [h2.get_text(" ", strip=True) for h2 in soup.find_all("h2")]
            image_srcs = [img["src"] for img in soup.find_all("img", src=True)]
            if ptexts[1] == "Host" or ptexts[1] == "Guest" or ptexts[1] == "Booker":
                message = ptexts[2]
                host = ptexts[1] == "Host"
                name = h2texts[0]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, message, name, host))
            else:
                message = ptexts[2]
                host = image_srcs[2] == "https://a0.muscache.com/im/pictures/user/89a57bc6-3c38-435c-807d-904e2bac20c1.jpg?aki_policy=profile_medium" 
                name = ptexts[1]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, message, name, host))
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
def query(messages):
    # build thread text and retrieve top-5 rules
    thread_text = "\n".join(m['text'] for m in messages) if messages else ""
    docs = vect_collection.query(
        query_texts=[thread_text], n_results=5, include=["documents"]
    ).get("documents", [[]])[0] if messages else []
    # combine static context and retrieved rules
    dynamic_ctx = "\n\n".join(docs)
    # assemble messages: system prompt + history
    tMessages = [
        SystemMessage(content=f"You are the host of an Oceanside house, your name is Tina Han."
                        f" Be warm, concise, and solution-oriented. Never share internal notes."
                        f" Follow HOUSE RULES and AIRBNB POLICIES below.\n\n{dynamic_ctx}")
    ] + [
        (AIMessage if m['role']=='host' else HumanMessage)(content=f"{m['name']} {m['text']}")
        for m in messages
    ]
    # invoke chat
    return get_openrouter_chat().invoke(tMessages).content
@app.route('/api/threads', methods=['GET'])
def get_threads():
    """Get all email threads with messages from database"""
    try:
        # Connect to database
        conn = sqlite3.connect("airbnb.db")
        cursor = conn.cursor()
        
        # Fetch the 100 most recent messages, then reverse for chronological order
        cursor.execute(
            """
            SELECT uid, thread_id, content, name, host
            FROM messages
            ORDER BY uid DESC
            LIMIT 100
            """
        )
        rows = cursor.fetchall()
        rows.reverse()
        threads_data = defaultdict(list)
        thread_names = {}
        for uid, thread_id, content, name, is_host in rows:
            # Store the first guest name per thread
            if not is_host and thread_id not in thread_names:
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
        # Generate AI response using enriched query helper
        response = query(messages)
        return jsonify({"response": response})
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
