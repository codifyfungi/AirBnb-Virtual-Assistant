import imaplib
import email
import re
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from collections import defaultdict
def fetch(em,password):

    threads = defaultdict(list)
    thread_name = {}

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
    host_id = "89a57bc6-3c38-435c-807d-904e2bac20c1"
    for uid in all_ids[:10]:
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

        with open("airbnb_message.html", "w", encoding="utf-8") as f:
            f.write(html_body)
        #print(html_body)
        #Retrieve message thread id
        m = re.search(
            r'href="https://www\.airbnb\.com/hosting/thread/(\d+)\?',html_body
        )
        if m:
            thread_id = m.group(1)
        m = re.search(
            r'(?<=/im/pictures/user/)[0-9a-fA-F-]+(?=\.jpg)',html_body
        )
        if m:
            messenger_id = m.group(0)
        #Find the message content
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
            parts = message.split()
            name = parts[0]
            message = " ".join(parts[1:])
            if messenger_id == host_id:
                message_data = {
                    "role": "host",
                    "text": message,
                    "name": name,
                    "time": "Recent"
                }
                threads[thread_id].append(message_data)
            else:
                message_data = {
                    "role": "guest",
                    "text": message,
                    "name": name,
                    "time": "Recent"
                }
                if thread_id not in thread_name:
                    thread_name[thread_id] = name
                threads[thread_id].append(message_data)
        else:
            print("Couldn't find the message block.")
    return (thread_name,threads)
