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
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch

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
    def count(self, x):
        return self.d.count(x)
    def __iter__(self):
        return iter(self.d)

chatqueuegeeks = dq()
chatqueueanime = dq()       
cntanime = counter(0)
cntgeeks = counter(0)
with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = sys.argv[1] if len(sys.argv) >1 else "MaidBot"  # Bot's nickname
CHANNELS = ["#geeks"]  # Channel to join

sys_instruct_init=f"Limit your output to 450 characters. You are {sys.argv[2]}"
sys_instruct_anime = f"Limit your output to 450 characters. You are {sys.argv[2]}. The request is of the format '[name]: [request]'.  You are in an IRC channel called #anime. Your name is {NICK}"
sys_instruct_geeks = f"Limit your output to 450 characters. You are {sys.argv[2]}. The request is of the format '[name]: [request]'.  You are in an IRC channel called #geeks. Your name is {NICK}"
sys_instruct_news="Limit your output to 2 paragraphs each at most 450 characters."
sys_instruct_art= f"You are {sys.argv[2]}.  Limit your output to 2 paragraphs each paragraph not more than 450 characters"

google_search_tool = Tool(google_search=GoogleSearch())

chatanime = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_anime),
    )

chatgeeks = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_geeks),
    )    

chatcubes = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_geeks),
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
    inputtext = event.arguments[0].strip()
    inputtext2 = event.arguments[0].strip()
    inputtext = event.source.nick + ": " + inputtext
    chan = event.target
    logging(event, inputtext)
    if event.arguments[0][:len(NICK)].lower().strip() == NICK.lower():
        if event.arguments[0].find("!news") != -1:
            get_ai_news(event, connection)
            return
#        get_ai_answer(inputtext, connection, event)
#        return
        if event.arguments[0].find("!art") != -1:
            get_ai_art(event, connection)
            return

    if event.target == "#anime":        
        cntanime.increment()
        chatqueueanime.append(event.source.nick + ": " + inputtext2)
        print(f"cntanime.msg: {cntanime.value}")
        if cntanime.value > 10:
            random_range = random.uniform(0, 40)
            print(f"random range: {random_range}")
            if cntanime.value > random_range:
                inputqueue = "; ".join(list(chatqueueanime))
                print(inputqueue)
                get_ai_answer(inputqueue, connection, event)
                cntanime.clear()
                print("***** resetting counter: #anime *****")
    if event.target == "#geeks":        
        cntgeeks.increment()
        chatqueuegeeks.append(event.source.nick + ": " + inputtext2)
        print(f"cntgeeks.msg: {cntgeeks.value}")
        if cntgeeks.value > 10:
            random_range = random.uniform(0, 40)
            print(f"random range: {random_range}")
            if cntgeeks.value > random_range:
                inputqueue = "; ".join(list(chatqueuegeeks))
                print(inputqueue)
                get_ai_answer(inputqueue, connection, event)
                cntgeeks.clear()
                print("***** resetting counter: #geeks *****")



def remove_lfcr(text):
    return text.replace("\n"," ").replace("\r"," ")

def get_ai_answer(inputtext, connection, event):
    if event.target == "#anime":
        response = chatanime.send_message(inputtext)
    if event.target == "#geeks":
        response = chatgeeks.send_message(inputtext)
    if event.target == "#cubes":
        response = chatcubes.send_message(inputtext)
    if response.text == "":
        return
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

def get_ai_news(event, connection):
    response = client.models.generate_content(
    model='gemini-2.0-flash-thinking-exp',
    config=types.GenerateContentConfig(system_instruction=sys_instruct_news, tools =[google_search_tool]),
    contents="What is the latest news?",
    )  
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(output)
        connection.privmsg(event.target,output)        
        time.sleep(1)
    return

def get_ai_art(event, connection):
    artlen = len(NICK) + 6
    print(artlen)
    image_path = event.arguments[0][artlen:]
    print(image_path)
    image = requests.get(image_path)
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_art),
        contents=["Criticise the image in the style of an art critic",
              types.Part.from_bytes(data=image.content, mime_type="image/jpeg")]
        )
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(output)
        connection.privmsg(event.target,output)        
        time.sleep(1)
    return

if __name__ == "__main__":
    main()

