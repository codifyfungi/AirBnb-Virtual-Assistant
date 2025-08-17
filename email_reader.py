import imaplib
import email
import re
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from collections import defaultdict
import sqlite3
from dotenv import load_dotenv
load_dotenv()
import os
import quopri
from bs4 import BeautifulSoup

conn = sqlite3.connect("airbnb.db")
cursor = conn.cursor()

# Create table for clients
# Create table for messages
# message id is email uid
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    content TEXT,
    name TEXT,
    host INTEGER,
    FOREIGN KEY (thread_id) REFERENCES clients(thread_id)
)
""")
def fetch(em,password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(em, password)
    mail.select("inbox")
    #Data is a list of byte strings
    status, data = mail.search(None,'(HEADER FROM "express@airbnb.com")')
    if status == "OK":
        print(data)
    #Create list of ids corresponding to an email
    all_ids = b" ".join(data).split()
    #print(all_ids)
    id = 0
    for uid in all_ids:
        status, msg_data = mail.fetch(uid,"(RFC822)")
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
            cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (id, thread_id, message, name, host))
            id += 1
        else:
            message = ptexts[2]
            host = image_srcs[2] == "https://a0.muscache.com/im/pictures/user/89a57bc6-3c38-435c-807d-904e2bac20c1.jpg?aki_policy=profile_medium" 
            name = ptexts[1]
            cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (id, thread_id, message, name, host))
            id += 1
EM = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
fetch(EM,PASSWORD)
conn.commit()
conn.close()