import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("Error: GROQ_API_KEY not found in .env file!")
else:
    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=20,
        )
        print("Connection Successful!")
        print("Model Response:", response.choices[0].message.content)
    except Exception as error:
        print("Connection Failed:", error)