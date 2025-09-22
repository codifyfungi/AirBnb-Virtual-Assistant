
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import imaplib
import email
import re
import threading
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime

from collections import defaultdict
import chromadb
from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction
from langchain_core.messages import trim_messages
from dotenv import load_dotenv
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import json

load_dotenv()

current_thread_id = None
app = Flask(__name__)

# Allow your Netlify front-end (and localhost) to hit every route
CORS(app, resources={r"/*": {"origins": "*"}})

lock = threading.Lock()
"""
Set up vector DB for rule retrieval using a free HuggingFace model.
"""
def init_db():
    conn = sqlite3.connect("airbnb.db")
    cursor = conn.cursor()

    # Create table for clients
    # Create table for messages
    # message id is email uid    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        listing_id TEXT PRIMARY KEY,
        address TEXT
    )
    """)    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id TEXT PRIMARY KEY,
        listing_id TEXT,
        guest_name TEXT,
        guest_image TEXT,
        guest_location TEXT,
        guest_type INT,
        guest_paid INT,
        host_payout INT,
        check_in_date TEXT,
        check_out_date TEXT,
        FOREIGN KEY (listing_id) REFERENCES listings (listing_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        uid INTEGER PRIMARY KEY,
        reservation_id TEXT,
        content TEXT,
        name TEXT,
        host INTEGER,
        FOREIGN KEY (reservation_id) REFERENCES listings (reservation_id)
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
    decoded_body = ""
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
                decoded_body = part.get_payload(decode=True).decode(charset, "replace") + "\n"
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
    return plain_body, decoded_body, html_body
@app.route('/api/host-answers', methods=['POST'])
def host_answers():
    """Accept host answers, use latest message as context for LLM reply (no vector DB)."""
    data = request.get_json()
    answers = data.get('hostAnswers', [])
    thread_id = current_thread_id
    # Fetch latest message from thread
    conn = sqlite3.connect("airbnb.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content, name, host FROM messages WHERE reservation_id = ? ORDER BY uid DESC LIMIT 1", (thread_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        content, name, is_host = row
        role = "host" if is_host else "guest"
        latest_msg = f"{role.title()}: {name}: {content}"
    else:
        latest_msg = ""
    # Compose LLM prompt
    llm = get_openrouter_chat()
    sys_msg = SystemMessage(content="Given the following latest message and host's answers, write a warm, helpful response to the guest.")
    host_context = "\n".join([f"Host answer: {a}" for a in answers])
    prompt = f"{latest_msg}\n\n{host_context}"
    human_msg = HumanMessage(content=prompt)
    reply = str(sys_msg) + '|' + str(human_msg)
    return jsonify({"response": reply})
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
        # Retrieve any new automated reservation emails with either Reminder, Confirmed, or Inquiry subjects
        status, data = mail.uid(
            "search", None,
            'UID', f'{last_uid+1}:*',
            'FROM', '"automated@airbnb.com"',
            'SUBJECT', '"Reservation Confirmed"'
        )

        auto_ids = b" ".join(data).split()        
        status, data = mail.uid(
            "search", None,
            'UID', f'{last_uid+1}:*',
            'FROM', '"automated@airbnb.com"',
            'SUBJECT', '"Inquiry"'
        )
        inq_ids = b" ".join(data).split()
        #Create list of ids corresponding to an email    
        status, data = mail.uid(
            "search", None,
            'UID', f'{last_uid+1}:*',
            'FROM', '"express@airbnb.com"'
        )
        express_ids = b" ".join(data).split()
        print("IDS")
        print(last_uid+1)
        for uid in inq_ids:
            status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
            uid = int(uid.decode())
            print(uid)
            msg = email.message_from_bytes(msg_data[0][1])
            plain_body,decoded_body, html_body = get_body(msg)
            soup = BeautifulSoup(html_body, "html.parser")
            ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            m = re.search(
                r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
                plain_body
            )
            reservation_id = m.group(1)
            list_m = re.search(r"https?://www\.airbnb\.com/rooms/(\d+)", plain_body)
            listing_id = list_m.group(1) if list_m else None
            guest_location = ptexts[2] if ptexts[1].startswith("Identity verified") else ptexts[1]
            # Extract guest name: inquiry or confirmed patterns
            guest_name = ptexts[0]
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
                if len(check_in_date.split(',')) < 3:
                    msg_date = parsedate_to_datetime(msg.get("Date"))
                    check_in_date += f", {msg_date.year}"
                    check_out_date += f", {msg_date.year}"
            # Override with direct muscache user image URL from either /im/pictures/user or /im/users/.../profile_pic
            guest_type = ptexts[-8]
            message = ptexts[3]
            if listing_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO listings (listing_id) VALUES (?)",
                    (listing_id,)
                )
            guest_image = None
            # Upsert reservation with detailed fields
            cursor.execute(
                """
                INSERT INTO reservations (
                    reservation_id,
                    listing_id,
                    guest_name,
                    guest_image,
                    guest_location,
                    guest_type,
                    guest_paid,
                    host_payout,
                    check_in_date,
                    check_out_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reservation_id) DO UPDATE SET
                    listing_id     = COALESCE(listing_id,     excluded.listing_id),
                    guest_name     = COALESCE(guest_name,     excluded.guest_name),
                    guest_image    = COALESCE(guest_image,    excluded.guest_image),
                    guest_location = COALESCE(guest_location, excluded.guest_location),
                    guest_type     = COALESCE(guest_type,     excluded.guest_type),
                    guest_paid     = COALESCE(guest_paid,     excluded.guest_paid),
                    host_payout    = COALESCE(host_payout,    excluded.host_payout),
                    check_in_date  = COALESCE(check_in_date,  excluded.check_in_date),
                    check_out_date = COALESCE(check_out_date, excluded.check_out_date)
                """,
                (reservation_id,
                    listing_id,
                    guest_name,
                    guest_image,
                    guest_location,
                    guest_type,
                    total_paid,
                    host_payout,
                    check_in_date,
                    check_out_date)
            )
            # sanitize text fields to remove invalid surrogates
            safe_message = message.encode('utf-8', 'replace').decode('utf-8')
            cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, safe_message, guest_name, 0))
        for uid in auto_ids:
            status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
            uid = int(uid.decode())
            msg = email.message_from_bytes(msg_data[0][1])
            plain_body,decoded_body, html_body = get_body(msg)
            soup = BeautifulSoup(html_body, "html.parser")
            ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            print(uid)
            m = re.search(
                r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
                plain_body
            )
            reservation_id = m.group(1)
            list_m = re.search(r"https?://www\.airbnb\.com/rooms/(\d+)", plain_body)
            listing_id = list_m.group(1) if list_m else None
            guest_location = ptexts[3] if ptexts[0].startswith("Send a message to confirm") else ptexts[2]
            # Extract guest name from Subject line
            # Extract guest name: inquiry or confirmed patterns
            guest_name = ptexts[1]
            # Extract number of adults and children
            for i in range(len(ptexts)):
                if ptexts[i] == "'Guests will now let them know if they’re bringing children and infants. Let them know upfront if your listing is suitable for children by updating your House Rules.'":
                    guest_type = ptexts[i-1]
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
            if len(check_in_date.split(',')) < 3:
                msg_date = parsedate_to_datetime(msg.get("Date"))
                check_in_date += f", {msg_date.year}"
                check_out_date += f", {msg_date.year}"
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
            if listing_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO listings (listing_id) VALUES (?)",
                    (listing_id,)
                )
            # Upsert reservation with detailed fields
            cursor.execute(
                """
                INSERT INTO reservations (
                    reservation_id,
                    listing_id,
                    guest_name,
                    guest_image,
                    guest_location,
                    guest_type,
                    guest_paid,
                    host_payout,
                    check_in_date,
                    check_out_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reservation_id) DO UPDATE SET
                    listing_id     = COALESCE(listing_id,     excluded.listing_id),
                    guest_name     = COALESCE(guest_name,     excluded.guest_name),
                    guest_image    = COALESCE(guest_image,    excluded.guest_image),
                    guest_location = COALESCE(guest_location, excluded.guest_location),
                    guest_type     = COALESCE(guest_type,     excluded.guest_type),
                    guest_paid     = COALESCE(guest_paid,     excluded.guest_paid),
                    host_payout    = COALESCE(host_payout,    excluded.host_payout),
                    check_in_date  = COALESCE(check_in_date,  excluded.check_in_date),
                    check_out_date = COALESCE(check_out_date, excluded.check_out_date)
                """,
                (reservation_id,
                    listing_id,
                    guest_name,
                    guest_image,
                    guest_location,
                    guest_type,
                    total_paid,
                    host_payout,
                    check_in_date,
                    check_out_date)
            )
        for uid in express_ids:
            status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
            uid = int(uid.decode())
            msg = email.message_from_bytes(msg_data[0][1])
            plain_body,_, html_body = get_body(msg)
            print(uid)
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
                safe_message = message.encode('utf-8', 'replace').decode('utf-8')
                host = ptexts[1] == "Host"
                name = h2texts[0]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, safe_message, name, host))
            else:
                message = ptexts[2]
                safe_message = message.encode('utf-8', 'replace').decode('utf-8')
                host = image_srcs[2] == "https://a0.muscache.com/im/pictures/user/89a57bc6-3c38-435c-807d-904e2bac20c1.jpg?aki_policy=profile_medium" 
                name = ptexts[1]
                cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, safe_message, name, host))
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

@app.route('/api/thread', methods=['GET'])
def get_thread():
    """Get the current email thread and its details"""
    thread_id = current_thread_id
    if not thread_id:
        return jsonify({"error": "No current thread set"}), 404
    try:
        conn = sqlite3.connect("airbnb.db")
        cursor = conn.cursor()
        # Fetch reservation details for current thread_id
        cursor.execute(
            "SELECT reservation_id, listing_id, guest_name, guest_image, guest_location, guest_type, check_in_date, check_out_date "
            "FROM reservations WHERE reservation_id = ?",
            (thread_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Thread not found"}), 404
        cols = [d[0] for d in cursor.description]
        thread_info = dict(zip(cols, row))
        # Fetch messages for this thread
        cursor.execute(
            "SELECT content, name, host FROM messages WHERE reservation_id = ? ORDER BY uid ASC",
            (thread_id,)
        )
        msgs = cursor.fetchall()
        messages = []
        for content, name, is_host in msgs:
            messages.append({
                "role": "host" if is_host else "guest",
                "name": name,
                "text": content
            })
        conn.close()
        return jsonify({"thread": thread_info, "messages": messages})
    except Exception as e:
        print(f"Error fetching thread {thread_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/getquestions', methods=['GET'])
def get_questions():
    """Fetch the last guest message for the current thread and return clarifying questions."""
    try:
        # --- Original dynamic LLM-based logic (commented out for testing) ---
        # conn = sqlite3.connect("airbnb.db")
        # cursor = conn.cursor()
        # cursor.execute(
        #     "SELECT content FROM messages WHERE reservation_id=? AND host=0 ORDER BY uid DESC LIMIT 1",  
        #     (current_thread_id,)
        # )
        # row = cursor.fetchone()
        # conn.close()
        # last_msg = row[0] if row else ""
        # llm = get_openrouter_chat()
        # sys_msg = SystemMessage(
        #     content="Given this guest's last message, return a JSON list of clarifying questions to ask the host.(It could be empty if no questions are needed.)"
        # )
        # human_msg = HumanMessage(content=last_msg)
        # raw = llm.invoke([sys_msg, human_msg])
        # try:
        #     questions = json.loads(raw)
        # except Exception:
        #     questions = [q.strip('- ').strip() for q in raw.splitlines() if q.strip()]
        # return jsonify({"questions": questions})
        # --- Testing stub: return a fixed set of clarifying questions ---
        questions = [
            "What time is the guest planning to arrive?",
            "Does the guest need any special accommodations?",
            "Will the guest be bringing additional guests?"
        ]
        return jsonify({"questions": questions})
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

# Keep the current thread ID in memory

@app.route("/api/current-thread", methods=["GET", "POST"])
def current_thread():
    global current_thread_id
    if request.method == "POST":
        data = request.get_json()
        # Expect { threadId: "<reservation_id>" }
        current_thread_id = data.get("threadId")
        print(current_thread_id)
        return ("", 204)
    # GET returns the last set threadId (or None)
    return jsonify({"threadId": current_thread_id})

# --- helper: generate questions for last message ---

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
