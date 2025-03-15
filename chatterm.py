from google import genai
from google.genai import types
from collections import deque
import requests
import time
import json
sys_instruct="You are the prim and proper head maid of an english stately home.  You are multi-talented and very intelligent. Limit your output to 450 characters"
with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)
chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=sys_instruct),
    )


while True:
    test = input("request:")
    print(test)

    response = chat.send_message(test)
    print(response.text)

    for message in chat._curated_history:
        print(f'role - {message.role}', end=": ")
        print(message.parts[0].text)
