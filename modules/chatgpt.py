from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

client = OpenAI(
    api_key=os.getenv('OPENAI_TOKEN'),
)

def send_message(content):
    response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": content}

            ],
        )
    # return "response"
    return response.choices[0].message.content
