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

argparse = sys.argv[0]
if len(sys.argv) < 2:
    print(f"Usage: {argparse} <config_file>")
    sys.exit(1)

class dq:
# deque for each channel of the random response routine
# this is a deque that holds the last 10 messages in the channel
    def __init__(self):
        self.d = deque(maxlen=10)
    def append(self, x):
        self.d.append(x)
    def count(self, x):
        return self.d.count(x)
    def __iter__(self):
        return iter(self.d)

# Load the API key from a file
with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

# IRC Server details
# load server details, nick, channels to join and system prompt from config file
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

# Load the configuration file
config = load_config()

# Print the configuration details to the console
print("=== IRC Bot Configuration ===")
print(f"Server: {config['server']['server']}")
print(f"Port: {config['server']['port']}")
print(f"Nickname: {config['general']['nick']}")
print(f"Channels: {config['general']['channels']}")
print(f"SysPrompt: {config['specifics']['sysprompt']}")

# Assign the configuration values to variables
SERVER = config['server']['server']
PORT = config['server']['port']
NICK = config['general']['nick']
CHANNELS = config['general']['channels']
SYSPROMPT = config['specifics']['sysprompt']

# Setup the system prompt and instructions
sys_instruct_init=f"Limit your output to 450 characters. You are {SYSPROMPT}"
sys_instruct_news=f"You are {SYSPROMPT}.  Limit your output to 1 paragraph each at most 450 characters."
sys_instruct_art= f"You are {SYSPROMPT}.  Limit your output to 1 paragraph each paragraph not more than 450 characters"

# Setup the Google Search tool
google_search_tool = Tool(google_search=GoogleSearch())

chats = {}
chatdeque = {}

# this connects to the server and joins the channels
def on_connect(connection, event):
    for chan in CHANNELS:
        sys_instruct = f"Limit your output to 450 characters. You are {SYSPROMPT}. The request is of the format '[name]: [request]'.  You don't have to use this format in your answers.  You are in an IRC channel called {chan}. Your name is {NICK}"
        chat = client.chats.create(
                model="gemini-2.5-flash-lite-preview-06-17",
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

# this is the main function that connects to the server and starts the bot
def main():
    reactor = irc.client.Reactor()
    try:
        c = reactor.server().connect(SERVER, PORT, NICK)
        c.add_global_handler("welcome", on_connect)         # this is the welcome message handler
        c.add_global_handler("pubmsg", on_message)          # this is the public message handler
        c.add_global_handler("action",on_action)            # this is the action handler
        reactor.process_forever()
    except irc.client.ServerConnectionError:
        print("Connection error")

# this is the action handler that handles actions in the channel
def on_action(connection,event):
# setup the imput text for the AI
    inputtext = event.arguments[0].strip()
    inputtext2 = event.arguments[0].strip()
    inputtext = "[" + event.source.nick + " " + inputtext + "]"
    chan = event.target
    logging(event, inputtext)
    if inputtext.find(NICK.lower()) != -1:
        get_ai_answer(inputtext, connection, event)             # this is the AI answer handler
        return

# this is the routine that handles the messages in public channels
def on_message(connection, event):
# setup the imput text for the AI
    inputtext = event.arguments[0].strip()
    inputtext2 = event.arguments[0].strip()
    inputtext = event.source.nick + ": " + inputtext
    chan = event.target
    logging(event, inputtext)
# check if the message has the bot's name in it 
# deals with the message if no other handlers are called
    get_ai_answer(inputtext, connection, event)
    # see if the bot will make a random response to a message
    random_range = random.uniform(0,40)
    print(f"random range: {random_range}")    
    if random_range < (8):                      # this is the chance of a random response (4 is 10%)
        print("*** Random routine has fired ***")
        try:
            get_ai_answer2(inputtext,connection,event)
            return
        except errors.APIError as e:
            print(e.code)
            print(e.message)
            connection.privmsg(event.target,"Random routine error!")
            return
    return

# this is the routine that removes line feeds and carriage returns from the text
def remove_lfcr(text):
    return text.replace("\n"," ").replace("\r"," ")

# this is the routine that gets the AI answer to the question
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
# splits the response into paragraphs and sends them to the channel with a delay of 1 second between each paragraph and a maximum of 450 characters each to avoid flooding the channel
    if response.text[:8] == "IMMATURE":
        connection.privmsg(event.target, "Immaturity alarm triggered!  Please be more mature in your conversations.  Your nick has been logged!")
        connection.privmsg(event.target, response.text[9:])
        return
    return

def get_ai_answer2(inputtext, connection, event):
    try:
        chan = event.target
        if chan in chats:
            response = chats[chan].send_message("Give a short overview of the maturity of the chat")
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
# splits the response into paragraphs and sends them to the channel with a delay of 1 second between each paragraph and a maximum of 450 characters each to avoid flooding the channel
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(output)
        connection.privmsg(event.target,output)        
        time.sleep(1)
    return

# this is the routine that gets the joining message for the channel
def connect_msg():
#    response = client.models.generate_content(
#        model="gemini-2.5-flash-lite-preview-06-17",
#        config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
#        contents="Create a suitable joining message for an IRC channel.",
#    )

    return "Immaturity Alarm Bot is now online.  Please be mature in your conversations or you will be logged and warned."

# this is the routine that logs the messages to the console
def logging(event, inputtext):
    print(event.target + ":" + event.source.nick + ": " + event.arguments[0])
    print(event.target + ":" + event.source.nick + ": " + inputtext)

if __name__ == "__main__":
    main()

