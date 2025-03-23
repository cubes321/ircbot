# 1st argument = bot's nickname
# 2nd argument = bot's character type - enclose in quotes if it contains spaces

import irc.client
import requests
import time
import json
from google import genai
from google.genai import types, errors
import time
import sys
import random
from collections import deque
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import configparser

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

#chatqueuegeeks = dq()
#chatqueueanime = dq()       
#cntanime = counter(0)
#cntgeeks = counter(0)

with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)



# IRC Server details

def load_config(config_file='config.ini'):
    try:
        config = configparser.ConfigParser()
        config.read(config_file)

        server_info = {
            'server': config['IRCServer']['server'],
            'port': int(config['IRCServer']['port'])
        }

        general_info = {
            'nick': config['General']['nick']
        }

        channels_str = config['General']['channels']
        channels_str = channels_str.strip('[]')
        channels = [ch.strip().strip("'\"") for ch in channels_str.split(',')]
        general_info['channels'] = channels
    
        return {
            'server': server_info,
            'general': general_info
        }

    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found")
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required configuration key: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

config = load_config()
print("=== IRC Bot Configuration ===")
print(f"Server: {config['server']['server']}")
print(f"Port: {config['server']['port']}")
print(f"Nickname: {config['general']['nick']}")
print(f"Channels: {config['general']['channels']}")

SERVER = config['server']['server']
PORT = config['server']['port']
NICK = config['general']['nick']
CHANNELS = config['general']['channels']

##SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
#PORT = 6667  # Standard IRC port
#NICK = sys.argv[1] if len(sys.argv) >1 else "MaidBot"  # Bot's nickname
#CHANNELS = ["#geeks", "#anime"]  # Channel to join

sys_instruct_init=f"Limit your output to 450 characters. You are {sys.argv[2]}"
#sys_instruct = f"Limit your output to 450 characters. You are {sys.argv[2]}. The request is of the format '[name]: [request]'.  You don't have to use this format in your answers.  You are in an IRC channel called #anime. Your name is {NICK}"
sys_instruct_news=f"You are {sys.argv[2]}.  Limit your output to 2 paragraphs each at most 450 characters."
sys_instruct_art= f"You are {sys.argv[2]}.  Limit your output to 2 paragraphs each paragraph not more than 450 characters"

google_search_tool = Tool(google_search=GoogleSearch())

chats = {}
chatdeque = {}

def on_connect(connection, event):
    for chan in CHANNELS:
        sys_instruct = f"Limit your output to 450 characters. You are {sys.argv[2]}. The request is of the format '[name]: [request]'.  You don't have to use this format in your answers.  You are in an IRC channel called {chan}. Your name is {NICK}"
        chat = client.chats.create(
                model="gemini-2.0-flash-thinking-exp",
                config=types.GenerateContentConfig(system_instruction=sys_instruct),                
                )
        chats[chan] = chat
        chatdeque[chan] = dq()
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
        c.add_global_handler("action",on_action)
        reactor.process_forever()
    except irc.client.ServerConnectionError:
        print("Connection error")

def on_action(connection,event):
    inputtext = event.arguments[0].strip()
    inputtext2 = event.arguments[0].strip()
    inputtext = "[" + event.source.nick + " " + inputtext + "]"
    chan = event.target
    logging(event, inputtext)
    if inputtext.find(NICK.lower()) != -1:
        get_ai_answer(inputtext, connection, event)
        return
#    if inputtext.find("cubes") != -1:
#        get_ai_answer(inputtext, connection, event)
#        return
#    if inputtext.find("buffet") != -1:
#        get_ai_answer(inputtext, connection, event)
#        return
#    if inputtext.find("ChatSec") != -1:
#        get_ai_answer(inputtext, connection, event)
#        return
#    if event.arguments[0].find("steal") != -1:
#        get_ai_answer(inputtext, connection, event)
#        return

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
        if event.arguments[0].find("!art") != -1:
            get_ai_art(event, connection)
            return
        get_ai_answer(inputtext, connection, event)
        return
    chatdeque[chan].append(event.source.nick + ": " + inputtext2)
    random_range = random.uniform(0,40)
    print(f"random range: {random_range}")    
    if random_range < (6):
        print("*** Random routine has fired ***")
        inputqueue = "; ".join(list(chatdeque[chan]))
        print(inputqueue)
        try:
            get_ai_answer(inputqueue,connection,event)
            return
        except errors.APIError as e:
            print(e.code)
            print(e.message)
            connection.privmsg(event.target,"Random routine error!")
            return

#    if event.target == "#anime":        
#        cntanime.increment()
#        chatqueueanime.append(event.source.nick + ": " + inputtext2)
#        print(f"cntanime.msg: {cntanime.value}")
#        if cntanime.value > 10:
#            random_range = random.uniform(0, 40)
#            print(f"random range: {random_range}")
#            if cntanime.value > random_range:
#                inputqueue = "; ".join(list(chatqueueanime))
#                print(inputqueue)
#                get_ai_answer(inputqueue, connection, event)
#                cntanime.clear()
#                print("***** resetting counter: #anime *****")

#    if event.target == "#geeks":        
#        cntgeeks.increment()
#        chatqueuegeeks.append(event.source.nick + ": " + inputtext2)
#        print(f"cntgeeks.msg: {cntgeeks.value}")
#        if cntgeeks.value > 10:
#            random_range = random.uniform(0, 40)
#            print(f"random range: {random_range}")
#            if cntgeeks.value > random_range:
#                inputqueue = "; ".join(list(chatqueuegeeks))
#                print(inputqueue)
#                get_ai_answer(inputqueue, connection, event)
#                cntgeeks.clear()
#                print("***** resetting counter: #geeks *****")



def remove_lfcr(text):
    return text.replace("\n"," ").replace("\r"," ")

def get_ai_answer(inputtext, connection, event):
    try:
        chan = event.target
        if chan in chats:
            response = chats[chan].send_message(inputtext)
        else:
            print(f"Error: No chat instance for channel {chan}")
            return
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIerror as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"Chat routine error!")
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
    try:
        response = client.models.generate_content(
        model='gemini-2.0-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news, tools =[google_search_tool]),
        contents="What is the latest news?",
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"News routine error!")
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

def get_ai_art(event, connection):
    artlen = len(NICK) + 6
    print(artlen)
    image_path = event.arguments[0][artlen:]
    print(image_path)
    image = requests.get(image_path)
# version 1 18/03/2025
    try:
      response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_art),
        contents=["Criticise the image in the style of an art critic",
              types.Part.from_bytes(data=image.content, mime_type="image/jpeg")]
        )
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"Art routine error!")
        return
# end of new error trapping routine
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

