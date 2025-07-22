import imaplib
import os
from dotenv import load_dotenv
import email
import re
from collections import defaultdict
load_dotenv() 
em = os.getenv("EMAIL")
password = os.getenv("PASSWORD")

def fetch(em,password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(em, password)
    mail.select("inbox")
    #Data is a list of byte strings
    status, data = mail.search(None,'(ALL HEADER FROM "express@airbnb.com")')
    if status == "OK":
        print(data)
    #Create list of ids corresponding to an email
    all_ids = b" ".join(data).split()
    #print(all_ids)
    threads = defaultdict(list)
    for i in range(100):
        status, msg_data = mail.fetch(all_ids[i],"(RFC822)")
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
                text    = part.get_payload(decode=True).decode(charset, errors="replace")

                if ctype == "text/plain":
                    # direct concatenation
                    plain_body += text + "\n\n"
                elif ctype == "text/html":
                    html_body += text + "\n\n"
        else:
            # single‑part message
            ctype   = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            text    = msg.get_payload(decode=True).decode(charset, errors="replace")
            if ctype == "text/plain":
                plain_body = text
            elif ctype == "text/html":
                html_body = text
        #print(html_body)
        m = re.search(
            r'href="https://www\.airbnb\.com/hosting/thread/(\d+)\?',html_body
        )
        if m:
            thread_id = m.group(1)
        
        #Find the message
        m = re.search(
            r"\[https://www\.airbnb\.com/help/article/209\?[^]]+\]\.\s*\n"
            #Non-Greedy, match as little as you can while matching the pattern
            r"(.*?)"
            r"(?=\nReply)",
            plain_body,
            flags=re.DOTALL
        )
        if m:
            message = m.group(1).strip()
            threads[thread_id].append(message)
        else:
            print("Couldn't find the message block.")  
    return threads
threads = fetch(em,password)
for thread_id,messages in threads.items():
    print(thread_id)
    for message in messages:
        print(message)