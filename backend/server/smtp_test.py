import os, smtplib, socket
from dotenv import load_dotenv
load_dotenv()

user = os.getenv("SMTP_USERNAME")
pwd = os.getenv("SMTP_PASSWORD")
ipv4 = socket.getaddrinfo("smtp.gmail.com", 465, socket.AF_INET)[0][4][0]
print("Using IPv4:", ipv4)

for label, fn in [
    ("465 SSL", lambda: smtplib.SMTP_SSL(ipv4, 465, timeout=20)),
    ("587 STARTTLS", lambda: smtplib.SMTP(ipv4, 587, timeout=20)),
]:
    try:
        s = fn()
        if "587" in label:
            s.starttls()
        s.login(user, pwd)
        print(label, "-> LOGIN OK")
        s.quit()
    except Exception as e:
        print(label, "-> FAILED:", type(e).__name__, e)