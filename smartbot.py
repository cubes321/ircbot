# 1st argument = bot's nickname
# 2nd argument = bot's character type - enclose in quotes if it contains spaces

import irc.client
import requests
import time
import json
from google import genai
from google.genai import types
import time
import sys
import random
from collections import deque

class counter:
    def __init__(self, value):
        self.value = value
    def increment(self):
        self.value += 1
    def clear(self):
        self.value = 0

class dq:
    def __init__(self):
        self.d = deque(maxlen=10)
    def append(self, x):
        self.d.append(x)

chatqueue = dq()        
cnt = counter(0)

with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = sys.argv[1] if len(sys.argv) >1 else "MaidBot"  # Bot's nickname
CHANNELS = ["#anime"]  # Channel to join

sys_instruct_init=f"Limit your output to 450 characters. You are {sys.argv[2]}"
sys_instruct = f"Limit your output to 450 characters. You are {sys.argv[2]}. The request is of the format '[name]: [request]'.  You are in an IRC channel called #anime. "

chat = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct),
    )

def on_connect(connection, event):
    for chan in CHANNELS:
       print("Joining channel: " + chan)
       connection.join(chan)
       result = connect_msg()
       result = remove_lfcr(result)
       print(result)
       connection.privmsg(chan, result)

def main():
    reactor = irc.client.Reactor()
    try:
        c = reactor.server().connect(SERVER, PORT, NICK)
        c.add_global_handler("welcome", on_connect)
        c.add_global_handler("pubmsg", on_message)
        reactor.process_forever()
    except irc.client.ServerConnectionError:
        print("Connection error")

def on_message(connection, event):
    inputtext = event.arguments[0][len(NICK):]
    inputtext2 = event.arguments[0].strip()
    logging(event, inputtext)
    inputtext = event.source.nick + ": " + inputtext
    chan = event.target
    if event.arguments[0][:len(NICK)].lower().strip() == NICK.lower():
        if chan == "#anime":
            get_ai_answer(inputtext, connection, event)
            return
#    cnt.msg += 1
    cnt.increment()
    chatqueue.append(inputtext)
    print(f"cnt.msg: {cnt.value}")
    if cnt.value > 10:
        random_range = random.uniform(0, 50)
        print(f"random range: {random_range}")
        if cnt.value > random_range:
            print(f"chatqueue: {" ".join(chatqueue)}")
#            print(f"inputtest: {inputtext}")
#            get_ai_answer(inputtext2, connection, event)
            get_ai_answer(" ".join(chatqueue), connection, event)
#            cnt.msg = 0
            cnt.clear()

def remove_lfcr(text):
    return text.replace("\n"," ").replace("\r"," ")

def get_ai_answer(inputtext, connection, event):
    response = chat.send_message(inputtext)
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(output)
        connection.privmsg(event.target,output)        
        time.sleep(1)
    return

def connect_msg():
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
        contents=f"Create a suitable joining message for an IRC channel.  Mention that you can be called by using {NICK} followed by a message.",
    )
    return response.text

def logging(event, inputtext):
    print(event.target + ":" + event.source.nick + ": " + event.arguments[0])
    print(event.target + ":" + event.source.nick + ": " + inputtext)

if __name__ == "__main__":
    main()

