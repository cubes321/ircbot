# 1st argument = config file
# TODO: re-write fire on specific word routine to fire using words taken from config file

import irc.client
import requests
import time
import json # <-- NEW: Imported for loading park_data.json
from google import genai
from google.genai import types, errors
import sys
import random
from collections import deque
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import configparser
import re
import yt_dlp
import datetime

argparse = sys.argv[0]
if len(sys.argv) < 2:
    print(f"Usage: {argparse} <config_file>")
    sys.exit(1)

class dq:
    # deque for each channel of the random response routine
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
            'sysprompt': config['Specifics']['sysprompt'],
            # --- MODIFIED: Reads the path to the new JSON database ---
            'database_file': config['Specifics']['database_file']
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
print(f"Database File: {config['specifics']['database_file']}")
print(f"SysPrompt Loaded: {len(config['specifics']['sysprompt'])} characters")


# Assign the configuration values to variables
SERVER = config['server']['server']
PORT = config['server']['port']
NICK = config['general']['nick']
CHANNELS = config['general']['channels']
SYSPROMPT = config['specifics']['sysprompt']

# Setup the system prompt and instructions
sys_instruct_init=f"Limit your output to 450 characters. You are {SYSPROMPT}"
sys_instruct_news=f"You are {SYSPROMPT}. Limit your output to 2 paragraphs each at most 450 characters."
sys_instruct_art= f"You are {SYSPROMPT}. Limit your output to 2 paragraphs each paragraph not more than 450 characters"

# Setup the Google Search tool
google_search_tool = Tool(google_search=GoogleSearch())

chats = {}
chatdeque = {}
final_sysprompt = "" # Will be populated in on_connect

# --- MODIFIED: Updated on_connect function ---
def on_connect(connection, event):
    # This message is crucial. If you don't see it, the bot never fully connected.
    print("--> Server welcome received! Now preparing to join channels...")

    global final_sysprompt
    try:
        print(f"--> Loading park database from: {config['specifics']['database_file']}")
        with open(config['specifics']['database_file'], 'r', encoding='utf-8') as f:
            park_data = json.load(f)

        database_string = "\n\nPARK DATABASE\n\n"
        for land, details in park_data.items():
            database_string += f"[{land}]\n"
            for category, items in details.items():
                for item in items:
                    database_string += f"    {category.rstrip('s')}: {item}\n"
            database_string += "\n"
        print("--> Park database loaded and formatted successfully.")

    except FileNotFoundError:
        print(f"!!! FATAL ERROR: Database file not found at {config['specifics']['database_file']}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"!!! FATAL ERROR: Could not parse the JSON in {config['specifics']['database_file']}. Error: {e}")
        sys.exit(1)

    base_prompt = SYSPROMPT
    final_sysprompt = base_prompt + database_string

    for chan in CHANNELS:
        sys_instruct = f"Limit your output to 450 characters. You are in an IRC channel called {chan}. Your name is {NICK}. Here are your instructions and data:\n{final_sysprompt}"
        chat = client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=sys_instruct),
                )
        chats[chan] = chat
        chatdeque[chan] = dq()
        print(f"--> Sending JOIN command for channel: {chan}")
        connection.join(chan)
        result = connect_msg()
        result = remove_lfcr(result)
        print(f"--> Sending welcome message to {chan}")
        connection.privmsg(chan, result)

def on_join(connection, event):
    if event.source.nick != connection.get_nickname():
        channel = event.target
        user = event.source.nick
        print(f"--> {user} has joined {channel}")

        welcome_message = welcome_msg(user)
        welcome_message = remove_lfcr(welcome_message)
        connection.privmsg(channel, welcome_message)

# --- NEW FUNCTION TO CATCH DISCONNECTIONS ---
def on_disconnect(connection, event):
    print(f"!!! DISCONNECTED from the server. Reason: {' '.join(event.arguments)}")
    # Optionally, you could add logic here to try and reconnect.

# --- NEW FUNCTION FOR ADVANCED DEBUGGING ---
# This will print every single message the server sends to the bot.
def on_raw_message(connection, event):
    print(f"<- RAW: {event.source} {event.type} {event.target} {' '.join(event.arguments)}")

# --- MODIFIED: Updated main function ---
def main():
    reactor = irc.client.Reactor()
    try:
        print(f"--> Attempting to connect to {SERVER}:{PORT} as {NICK}...")
        c = reactor.server().connect(SERVER, PORT, NICK)

        c.add_global_handler("welcome", on_connect)
        c.add_global_handler("pubmsg", on_message)
        c.add_global_handler("action",on_action)
        c.add_global_handler("join", on_join)
        c.add_global_handler("disconnect", on_disconnect) # <-- NEW
        # c.add_global_handler("all_events", on_raw_message) # <-- UNCOMMENT FOR VERY VERBOSE DEBUGGING

        print("--> Waiting for the server to welcome us...")
        reactor.process_forever()
    except irc.client.ServerConnectionError as e:
        print(f"!!! Connection error: {e}")
        sys.exit(1) # Exit if connection fails
    except Exception as e:
        print(f"An unexpected error occurred in main(): {e}")
        sys.exit(1)


def on_action(connection,event):
    inputtext = event.arguments[0].strip()
    inputtext2 = event.arguments[0].strip()
    inputtext = "[" + event.source.nick + " " + inputtext + "]"
    chan = event.target
    logging(event, inputtext)
    if inputtext.find(NICK.lower()) != -1:
        get_ai_answer(inputtext, connection, event)
        return

def on_message(connection, event):
    message_text = event.arguments[0]
    chan = event.target

    is_yt_command = "!yt" in message_text or "!animeyt" in message_text
    yt_url_pattern = r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+))'
    match = re.search(yt_url_pattern, message_text)

    if match and not (NICK.lower() in message_text.lower() and is_yt_command):
        url = match.group(1)
        video_info = get_youtube_video_info(url)
        if video_info:
            connection.privmsg(chan, video_info)

    inputtext = message_text.strip()
    inputtext2 = message_text.strip()
    inputtext = event.source.nick + ": " + inputtext
    logging(event, inputtext)

    if NICK.lower() in message_text.lower():
 #       if event.arguments[0].find("!help") != -1:
 #           help_text = f"Commands: !news, !art <url>, !yt <url>, !animeyt <url>, !meme, !help. Talk to me by mentioning my name, {NICK}."
 #           connection.privmsg(chan, help_text)
 #           return
        if event.arguments[0].find("!news") != -1:
            get_ai_news(event, connection)
            return
        if event.arguments[0].find("!art") != -1:
            get_ai_art(event, connection)
            return
        if event.arguments[0].find("!yt") != -1:
            get_yt_vid(event, connection)
            return
        if event.arguments[0].find("!animeyt") != -1:
            get_yt_animevid(event, connection)
            return
        if event.arguments[0].find("!meme") != -1:
            get_ai_meme(event, connection, chan)
            return
        get_ai_answer(inputtext, connection, event)
        return

    chatdeque[chan].append(event.source.nick + ": " + inputtext2)
    random_range = random.uniform(0,40)
    print(f"random range: {random_range}")
    if random_range < (4):
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

def remove_lfcr(text):
    return text.replace("\n"," ").replace("\r"," ")

def get_ai_answer(inputtext, connection, event):
    try:
        chan = event.target
        if chan in chats:
            # Use the globally defined final_sysprompt for context if needed, though chat object retains it
            response = chats[chan].send_message(inputtext)
        else:
            print(f"Error: No chat instance for channel {chan}")
            return
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(f"API Error in get_ai_answer: {e}")
        connection.privmsg(event.target,"Chat routine error!")
        return
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(f"--> Sending to {event.target}: {output}")
        connection.privmsg(event.target,output)
        time.sleep(1)
    return

def connect_msg():
    # This prompt is now simpler as the main context is in the chat object
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=final_sysprompt),
        contents=f"In character, create a suitable joining message for an IRC channel. Mention that you can be called by using {NICK} in the message.",
    )
    return response.text

def welcome_msg(user_nick):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=final_sysprompt),
            contents=f"In character, create a short and friendly welcome message for the user '{user_nick}' who has just joined the channel.",
        )
        return response.text
    except errors.APIError as e:
        print(f"Error generating welcome message: {e}")
        return f"Welcome, {user_nick}!"

def get_youtube_video_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'force_generic_extractor': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'Could not find title')
            channel = info_dict.get('uploader', 'N/A')
            duration_seconds = info_dict.get('duration', 0)
            if duration_seconds:
                td = datetime.timedelta(seconds=duration_seconds)
                duration_str = str(td)
            else:
                duration_str = "N/A (likely a live stream)"
            return f"YouTube: {title} | By: {channel} | Duration: {duration_str}"
    except yt_dlp.utils.DownloadError as e:
        print(f"Error fetching YouTube info for {url}: {e}")
        return "Could not retrieve info for that YouTube link."
    except Exception as e:
        print(f"An unexpected error occurred in get_youtube_video_info: {e}")
        return None

def logging(event, inputtext):
    print(event.target + ":" + event.source.nick + ": " + inputtext)

def get_ai_news(event, connection):
    try:
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news, tools =[google_search_tool]),
        contents="What is the latest news? Answer in character.",
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(f"API Error in get_ai_news: {e}")
        connection.privmsg(event.target,"News routine error!")
        return
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(f"--> Sending to {event.target}: {output}")
        connection.privmsg(event.target,output)
        time.sleep(1)
    return

def get_ai_art(event, connection):
    SUPPORTED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]
    artlen = len(NICK) + 6
    image_url = event.arguments[0][artlen:].strip()
    print(f"Attempting to fetch image from: {image_url}")

    try:
        image_response = requests.get(image_url, stream=True, timeout=10)
        image_response.raise_for_status()
        mime_type = image_response.headers.get('Content-Type')
        print(f"Detected MIME type: {mime_type}")

        if not mime_type or mime_type.split(';')[0] not in SUPPORTED_MIME_TYPES:
            error_msg = f"Unsupported or unknown image type: {mime_type}. Please use a direct link to a JPG, PNG, or WEBP file."
            print(error_msg)
            connection.privmsg(event.target, error_msg)
            return
        image_content = image_response.content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        connection.privmsg(event.target, "Could not fetch the image. Please check the URL.")
        return

    try:
      response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_art),
        contents=["Criticise the image in the style of an art critic",
              types.Part.from_bytes(data=image_content, mime_type=mime_type)]
        )
    except errors.APIError as e:
        print(f"API Error in get_ai_art: {e}")
        connection.privmsg(event.target, "Art routine error! The image may be invalid or corrupted.")
        return
    except Exception as e:
        print(f"An unexpected error occurred in get_ai_art: {e}")
        connection.privmsg(event.target, "An unexpected error occurred while analyzing the art.")
        return

    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(f"--> Sending to {event.target}: {output}")
        connection.privmsg(event.target,output)
        time.sleep(1)
    return

def get_yt_vid(event,connection):
    try:
        connection.privmsg(event.target,"<Analysing video please wait>")
        artlen = len(NICK) + 5
        yt_file = event.arguments[0][artlen:]
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news),
        contents=types.Content(
            parts=[
                types.Part(text='Summarize this video in character. A maximum of 3 paragraphs and 450 characters each.',),
                types.Part(file_data=types.FileData(file_uri=yt_file))
                ]
            )
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(f"API Error in get_yt_vid: {e}")
        connection.privmsg(event.target,"YT routine error!")
        return
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(f"--> Sending to {event.target}: {output}")
        connection.privmsg(event.target,output)
        time.sleep(1)
    return

def get_yt_animevid(event,connection):
    try:
        connection.privmsg(event.target,"<Analysing video please wait>")
        artlen = len(NICK) + 10
        yt_file = event.arguments[0][artlen:]
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news),
        contents=types.Content(
            parts=[
                types.Part(text='What do you think of this anime video? A maximum of 3 paragraphs and 450 characters each.',),
                types.Part(file_data=types.FileData(file_uri=yt_file))
                ]
            )
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(f"API Error in get_yt_animevid: {e}")
        connection.privmsg(event.target,"YT routine error!")
        return
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(f"--> Sending to {event.target}: {output}")
        connection.privmsg(event.target,output)
        time.sleep(1)
    return

def get_ai_meme(event,connection, chan):
    try:
        inputqueue = "; ".join(list(chatdeque[chan]))
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news),
        contents=f"{inputqueue}. Find a meme for this conversation. Respond with a link along with a sentence or two about the meme.",
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(f"API Error in get_ai_meme: {e}")
        connection.privmsg(event.target,"Meme routine error!")
        return
    para_text = response.text.splitlines()
    nonempty_para_text = [line for line in para_text if line.strip()]
    for paragraph in nonempty_para_text:
        output = remove_lfcr(paragraph)
        output = output[:450]
        print(f"--> Sending to {event.target}: {output}")
        connection.privmsg(event.target,output)
        time.sleep(1)
    return


if __name__ == "__main__":
    main()
