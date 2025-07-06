import imaplib
import os
from dotenv import load_dotenv
import email
import re
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
    print(all_ids)
    for i in range(10):
        status, msg_data = mail.fetch(all_ids[i],"(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        # msg is your email.message.Message from msg_data[0][1]
        if msg.is_multipart():
            # Walk each part, think of these as nodes in a tree, we only care about leaf nodes that are plain text
            for part in msg.walk():
                # Skip internal nodes
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    #Decode bytes to chars
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
            else:
                body = ""
        else:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        #Find the message
        pattern = re.compile(
            r"\[https://www\.airbnb\.com/help/article/209\?[^]]+\]\.\s*\n"
            #Non-Greedy, match as little as you can while matching the pattern
            r"(.*?)"
            r"(?=\nReply)",
            re.DOTALL
        )
        m = pattern.search(body)
        if m:
            message = m.group(1).strip()
            print(message)
        else:
            print("Couldn't find the message block.")
print(password)
fetch(em,password)