from openai import OpenAI
from gtts import gTTS
import gradio as gr
import os
from dotenv import load_dotenv
import tempfile
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

history = []


def speak(text):
    tts = gTTS(text)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_file.name)
    return temp_file.name

def respond(audio):
    global history

    # Transcribe audio to text using OpenAI Whisper
    with open(audio, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )

    user_input = transcript.text
    print("You said:", user_input)

    # Build GPT messages
    messages = [{"role": "system", "content": "You are a helpful habit tracking assistant. Please respond without using any markdown formatting (no asterisks, no underscores)."}]
    messages += history
    messages.append({"role": "user", "content": user_input})

    # Get response
    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages
    )
    reply = completion.choices[0].message.content

    # Update history
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    # Convert reply to audio
    reply_audio = speak(reply)

    return reply, reply_audio

# Gradio interface
app = gr.Interface(
    fn=respond,
    inputs=gr.Audio(type="filepath", label="Speak to your assistant"),
    outputs=[gr.Text(label="Assistant"), gr.Audio(label="Speaking back")]
)


app.launch()
