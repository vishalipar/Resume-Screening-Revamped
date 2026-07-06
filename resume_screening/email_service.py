import requests
from decouple import config

BREVO_API_KEY = config("BREVO_API_KEY")

def send_brevo_email(to_email, subject, html_content):
    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    payload = {
        "sender": {
            "name": "Resume Screening",
            "email": "sampleemail811@gmail.com"   # Your verified sender
        },
        "to": [
            {"email": to_email}
        ],
        "subject": subject,
        "htmlContent": html_content
    }

    response = requests.post(url, headers=headers, json=payload)

    response.raise_for_status()

    return response.json()