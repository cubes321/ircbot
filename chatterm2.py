from google import genai
from google.genai import types
from collections import deque
import requests
import time
import json
import re
sys_instruct="Limit your output to two paragraphs each at most 450 characters."
with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)



while True:
    test = input("request:")
    print(test)

    response = client.models.generate_content(
    model='gemini-2.0-flash-thinking-exp',
    config=types.GenerateContentConfig(system_instruction=sys_instruct),
    contents=test,
)
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    testnum = (1)
    for paragraph in nonempty_para_text:
        print(testnum)
        testnum = (testnum + 1)
        print(paragraph + "XX")
#    print(response.text)

