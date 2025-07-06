import imaplib
import os
from dotenv import load_dotenv
import email
from email.policy import default
load_dotenv() 
em = os.getenv("EMAIL")
password = os.getenv("PASSWORD")

def fetch(em,password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(em, password)
    mail.select("inbox")
    status, data = mail.search(None,'(ALL HEADER FROM "express@airbnb.com")')
    if status == "OK":
        print(data)
    all_ids = b" ".join(data).split()
    print(all_ids)
    status, msg_data = mail.fetch(all_ids[0],"(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    print(msg["Subject"])
print(password)
fetch(em,password)