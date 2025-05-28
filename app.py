from openai import OpenAI
import gradio as gr
import os
from dotenv import load_dotenv
import json
import smtplib
from email.message import EmailMessage
import csv

port = int(os.environ.get("PORT", 7860))

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_PASS")

history = []

# Ensure contacts file exists
if not os.path.exists("contacts.csv"):
    with open("contacts.csv", "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email"])
        writer.writeheader()

# Load contacts from CSV
def load_contacts(filename="contacts.csv"):
    contacts = {}
    try:
        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row["name"].strip().lower()
                email = row["email"].strip()
                contacts[name] = email
        print(f"Loaded {len(contacts)} contacts.")
    except Exception as e:
        print(f"Error loading contacts: {e}")
    return contacts

contacts = load_contacts()

def add_contact(name, email, filename="contacts.csv"):
    name = name.strip().lower()
    email = email.strip()
    if not name or not email:
        return "Name and email are required."
    if name in contacts:
        return f"{name} is already in your contacts."

    try:
        with open(filename, "a", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["name", "email"])
            writer.writerow({"name": name, "email": email})
        contacts[name] = email
        return f"Contact '{name}' added successfully."
    except Exception as e:
        return f"Failed to add contact: {str(e)}"

def find_recipient_email(transcript_text, contacts):
    contacts_str = "\n".join(f"{name}: {email}" for name, email in contacts.items())

    prompt = f"""
You are an assistant that helps identify which contact a user is referring to from a list.

User said: "{transcript_text}"

Here is the contact list:
{contacts_str}

Find the contact whose name best matches what the user said (even if spelled or pronounced differently).
Return the contact as JSON with fields "name" and "email".  
If no match, return an empty JSON object {{}}.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        temperature=0
    )

    reply = response.choices[0].message.content.strip()
    try:
        contact = json.loads(reply)
        if "name" in contact and "email" in contact:
            return contact["email"], contact["name"]
    except Exception:
        pass
    return None, None

def respond(audio_path):
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    user_input = transcript.text
    print("You said:", user_input)

    recipient_email, recipient_name = find_recipient_email(user_input, contacts)

    if not recipient_email:
        return "", "", "Recipient not found in contacts. Please say the recipient's full name clearly."

    system_message = {
        "role": "system",
        "content": (
            "You are a helpful assistant that writes professional emails based on user instructions. "
            "Generate a subject line and the email body text. "
            "End the email body with 'Kind Regards', then 'Jayden Vivar', and then my phone number '0424 420 712'. "
            "Respond only with the subject and body in this JSON format: "
            '{"subject": "<subject line>", "body": "<email body>"} '
            "Important: Make sure the JSON is valid. Use regular newline characters (\\n) for line breaks — do not double escape them."
        )
    }

    messages = [system_message] + history
    messages.append({"role": "user", "content": f"Recipient email: {recipient_email}. Instructions: {user_input}"})

    completion = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    reply = completion.choices[0].message.content
    print("Raw AI reply:", reply)

    try:
        email_data = json.loads(reply) if isinstance(reply, str) else reply
    except Exception as e:
        print("JSON parsing error:", e)
        email_data = {"subject": "", "body": str(reply)}

    subject = email_data.get("subject", "")
    body = email_data.get("body", "")

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = recipient_email
        msg.set_content(body, subtype='plain')
        html_body = body.replace('\n', '<br>')

        html_template = f"""\
        <!DOCTYPE html>
        <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Nexa Web Dev</title>
            <style>
              body {{
                margin: 0;
                padding: 0;
                background-color: #050505;
                font-family: Arial, sans-serif;
                color: #ffffff;
              }}
              .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #050505;
                border-radius: 6px;
                overflow: hidden;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
              }}
              .header {{
                background-color: #000000;
                color: #ffffff;
                text-align: center;
                padding: 10px;
              }}
              .header img {{
                height: 100px;
              }}
              .content {{
                padding: 30px;
                font-size: 16px;
                line-height: 1.6;
                color: white;
              }}
              .button {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 20px;
                background-color: #0077cc;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
              }}
              .footer {{
                text-align: center;
                font-size: 12px;
                color: #888888;
                padding: 20px;
              }}
              @media only screen and (max-width: 600px) {{
                .content {{
                  padding: 20px;
                }}
              }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <img style="height: 10rem" src="https://nexawebdev.com/assets/nexa_logo.svg" alt="logo" />
              </div>
              <div class="content">
                {html_body}<br />
                <a href="https://nexawebdev.com" style="
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 20px;
                    background-color: #0077cc;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: bold;
                ">Visit Website</a>
              </div>
              <div class="footer">
                &copy; 2025 Nexa Web. All rights reserved.<br />
                contact.nexawebdev@gmail.com<br />
                Sydney, NSW Australia
              </div>
            </div>
          </body>
        </html>
        """

        msg.add_alternative(html_template, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        send_status = f"Email successfully sent to {recipient_name} ({recipient_email})."
    except Exception as e:
        send_status = f"Failed to send email: {str(e)}"

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    return subject, body, send_status


# Gradio UI with Tabs
with gr.Blocks() as demo:
    gr.HTML(
        """<div style="text-align:center;"><img src="https://nexawebdev.com/assets/nexa_logo.svg" style="height:10rem;"></div>""")
    gr.Markdown("## Voice-to-Email App with Contact Manager")
    with gr.Tab("Send Email"):
        audio_input = gr.Audio(sources=["microphone"], type="filepath",
                               label="Say your email request including recipient's name")
        subject_out = gr.Textbox(label="Email Subject")
        body_out = gr.Textbox(label="Email Body")
        status_out = gr.Textbox(label="Send Status")
        audio_input.change(fn=respond, inputs=audio_input, outputs=[subject_out, body_out, status_out])

    with gr.Tab("Manage Contacts"):
        gr.Markdown("### 📇 Add New Contact")
        name_input = gr.Textbox(label="Name")
        email_input = gr.Textbox(label="Email")
        add_button = gr.Button("Add Contact")
        add_status = gr.Textbox(label="Add Status")
        add_button.click(fn=add_contact, inputs=[name_input, email_input], outputs=add_status)

        gr.Markdown("### 📋 Current Contacts")
        contact_table = gr.Dataframe(headers=["Name", "Email"], interactive=False)


        def get_contacts_df():
            contacts = load_contacts()
            return [[name, email] for name, email in contacts.items()]


        refresh_button = gr.Button("Show Contacts")
        refresh_button.click(fn=get_contacts_df, inputs=[], outputs=contact_table)

        gr.Markdown("### ❌ Delete Contact")
        delete_name = gr.Textbox(label="Name to Delete")
        delete_status = gr.Textbox(label="Delete Status")


        def delete_contact(name, filename="contacts.csv"):
            name = name.strip().lower()
            if name not in contacts:
                return f"No contact found with name: {name}"
            del contacts[name]
            try:
                with open(filename, "w", newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=["name", "email"])
                    writer.writeheader()
                    for n, e in contacts.items():
                        writer.writerow({"name": n, "email": e})
                return f"Contact '{name}' deleted successfully."
            except Exception as e:
                return f"Failed to delete contact: {str(e)}"


        delete_button = gr.Button("Delete Contact")
        delete_button.click(fn=delete_contact, inputs=delete_name, outputs=delete_status)

demo.launch(server_name="0.0.0.0", server_port=port, share=False)
