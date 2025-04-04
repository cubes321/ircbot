# 1st argument = config file
# TODO: re-write fire on specific word routine to fire using words taken from config file

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

with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

# IRC Server details

def load_config(config_file=sys.argv[1]):
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

        specifics_info = {
            'sysprompt': config['Specifics']['sysprompt']
        }
        channels_str = config['General']['channels']
        channels_str = channels_str.strip('[]')
        channels = [ch.strip().strip("'\"") for ch in channels_str.split(',')]
        general_info['channels'] = channels


        return {
            'server': server_info,
            'general': general_info,
            'specifics': specifics_info
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
print(f"SysPrompt: {config['specifics']['sysprompt']}")

SERVER = config['server']['server']
PORT = config['server']['port']
NICK = config['general']['nick']
CHANNELS = config['general']['channels']
SYSPROMPT = config['specifics']['sysprompt']


sys_instruct=f" Limit your output to 450 characters. You are {SYSPROMPT}."
google_search_tool = Tool(google_search=GoogleSearch())

chats = {}
chatdeque = {}

def on_connect(connection, event):
    for chan in CHANNELS:
        sys_instruct = f"On each message determine whether you should answer.  If no answer is required respond with 'NOANSWER - [reason for no answer] . The messages are of the form '[name]: [request]'.  You don't have to use this format in your answers.  You are {SYSPROMPT}.  You are in an IRC channel called {chan}. Your name is {NICK}.  Limit your output to 450 characters. "
        chat = client.chats.create(
                model="gemini-2.0-flash",
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
    get_ai_answer(inputtext, connection, event)

def on_message(connection, event):
    inputtext = event.arguments[0].strip()
    inputtext2 = event.arguments[0].strip()
    inputtext = event.source.nick + ": " + inputtext
    chan = event.target
    logging(event, inputtext)
    get_ai_answer(inputtext, connection, event)


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
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"Chat routine error!")
        return    
    if response.text[:8] == "NOANSWER":
        print(f"No answer required. Reason: {response.text[9:]}")
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
        config=types.GenerateContentConfig(system_instruction=sys_instruct),
        contents=f"Create a suitable joining message for an IRC channel.  Mention that you can be called by using {NICK} followed by a message.",
    )
    return response.text

def logging(event, inputtext):
    print(event.target + ":" + event.source.nick + ": " + event.arguments[0])
    print(event.target + ":" + event.source.nick + ": " + inputtext)

if __name__ == "__main__":
    main()

