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
import re
import yt_dlp # <-- NEW: Imported the yt-dlp library
import datetime # <-- NEW: Imported for formatting the duration

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
sys_instruct_news=f"You are {SYSPROMPT}.  Limit your output to 2 paragraphs each at most 450 characters."
sys_instruct_art= f"You are {SYSPROMPT}.  Limit your output to 2 paragraphs each paragraph not more than 450 characters"

# Setup the Google Search tool
google_search_tool = Tool(google_search=GoogleSearch())

chats = {}
chatdeque = {}

# this connects to the server and joins the channels
def on_connect(connection, event):
    for chan in CHANNELS:
        sys_instruct = f"Limit your output to 450 characters. You are {SYSPROMPT}. The request is of the format '[name]: [request]'.  You don't have to use this format in your answers.  You are in an IRC channel called {chan}. Your name is {NICK}"
        chat = client.chats.create(
                model="gemini-2.5-flash",
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

# This function handles the event when a user joins a channel
def on_join(connection, event):
    # Check if the user joining is not the bot itself
    if event.source.nick != connection.get_nickname():
        channel = event.target
        user = event.source.nick
        print(f"{user} has joined {channel}")
        
        # Generate and send a welcome message
        welcome_message = welcome_msg(user)
        welcome_message = remove_lfcr(welcome_message)
        connection.privmsg(channel, welcome_message)

# this is the main function that connects to the server and starts the bot
def main():
    reactor = irc.client.Reactor()
    try:
        c = reactor.server().connect(SERVER, PORT, NICK)
        c.add_global_handler("welcome", on_connect)         # this is the welcome message handler
        c.add_global_handler("pubmsg", on_message)          # this is the public message handler
        c.add_global_handler("action",on_action)            # this is the action handler
        c.add_global_handler("join", on_join)
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
    # setup the input text for the AI
    message_text = event.arguments[0]
    chan = event.target

    # *** MODIFIED *** Check for YouTube links and post info, but not for AI commands
    is_yt_command = "!yt" in message_text or "!animeyt" in message_text
    # Regex to find youtube URLs (handles youtube.com and youtu.be)
    yt_url_pattern = r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+))'
    match = re.search(yt_url_pattern, message_text)
    
    # If a URL is found AND it's not part of an AI command that already processes URLs, get the title/duration
    if match and not (NICK.lower() in message_text.lower() and is_yt_command):
        url = match.group(1)
        video_info = get_youtube_video_info(url)
        if video_info:
            connection.privmsg(chan, video_info)

    # The rest of the original on_message function follows
    inputtext = message_text.strip()
    inputtext2 = message_text.strip()
    inputtext = event.source.nick + ": " + inputtext
    logging(event, inputtext)
    
    # Check if the message contains the bot's name anywhere, not just at the start.
    if NICK.lower() in message_text.lower():
        # *** NEW *** Add a help command
        if event.arguments[0].find("!help") != -1:
            help_text = f"Commands: !news, !art <url>, !yt <url>, !animeyt <url>, !meme, !help. Talk to me by mentioning my name, {NICK}."
            connection.privmsg(chan, help_text)
            return
        # goes to the news routine if the message has !news in it
        if event.arguments[0].find("!news") != -1:
            get_ai_news(event, connection)
            return
        # goes to the art routine if the message has !art in it
        if event.arguments[0].find("!art") != -1:
            get_ai_art(event, connection)
            return
        # goes to the youtube routine if the message has !meme in it
        if event.arguments[0].find("!yt") != -1:
            get_yt_vid(event, connection)
            return
        # goes to the youtube anime routine if the message has !animeyt in it
        if event.arguments[0].find("!animeyt") != -1:
            get_yt_animevid(event, connection)
            return
        # goes to the meme routine if the message has !meme in it
        if event.arguments[0].find("!meme") != -1:
            get_ai_meme(event, connection, chan)
            return
        # deals with the message if no other handlers are called
        get_ai_answer(inputtext, connection, event)
        return
        
    # add the message to the deque for the channel to be used in the random routine
    chatdeque[chan].append(event.source.nick + ": " + inputtext2)
    # see if the bot will make a random response to a message
    random_range = random.uniform(0,40)
    print(f"random range: {random_range}")    
    if random_range < (4):                      # this is the chance of a random response (4 is 10%)
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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
        contents=f"Create a suitable joining message for an IRC channel.  Mention that you can be called by using {NICK} followed by a message.",
    )
    return response.text

# This routine generates a welcome message for a specific user.
def welcome_msg(user_nick):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
            contents=f"In character, create a short and friendly welcome message for the user '{user_nick}' who has just joined the channel.",
        )
        return response.text
    except errors.APIError as e:
        print(f"Error generating welcome message: {e}")
        return f"Welcome, {user_nick}!"

# This routine now uses yt-dlp to get video info, including the channel name.
def get_youtube_video_info(url):
    """
    Uses yt-dlp to get the title, uploader, and duration of a YouTube video.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'force_generic_extractor': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'Could not find title')
            channel = info_dict.get('uploader', 'N/A')
            duration_seconds = info_dict.get('duration', 0)
            
            if duration_seconds:
                # Format the duration from seconds to H:M:S or M:S
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

# this is the routine that logs the messages to the console
def logging(event, inputtext):
    print(event.target + ":" + event.source.nick + ": " + event.arguments[0])
    print(event.target + ":" + event.source.nick + ": " + inputtext)

# this is the routine that gets the news from the AI
def get_ai_news(event, connection):
    try:
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news, tools =[google_search_tool]),
        contents="What is the latest news?  Answer in character.",
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"News routine error!")
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

# this is the routine that gets the AI art from the image URL (jpg only)
def get_ai_art(event, connection):
    artlen = len(NICK) + 6
    print(artlen)
    image_path = event.arguments[0][artlen:]
    print(image_path)
    try:
        image = requests.get(image_path) # this gets the image from the URL
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        connection.privmsg(event.target,"Art routine error!")
        return
# version 1 18/03/2025
    try:
      response = client.models.generate_content(
        model="gemini-2.5-flash",
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

# this is the routine that gets a repsonse for a youtube video URL  
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
                types.Part(text='Summarize this video in character.  A maximum of 3 paragraphs and 450 characters each.',),
                types.Part(file_data=types.FileData(file_uri=yt_file))
                ]
            )
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"YT routine error!")
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

# this is the routine that gets a repsonse for a youtube anime video URL
def get_yt_animevid(event,connection):
    print("=== YT Anime ===")
    try:
        connection.privmsg(event.target,"<Analysing video please wait>")
        artlen = len(NICK) + 10
        print(f"event: {event.arguments[0]}")
        yt_file = event.arguments[0][artlen:]
        print(f"YT File: {yt_file}")
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news),
        contents=types.Content(
            parts=[
                types.Part(text='What do you think of this anime video?  A maximum of 3 paragraphs and 450 characters each.',),
                types.Part(file_data=types.FileData(file_uri=yt_file))
                ]
            )
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"YT routine error!")
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

# this is the routine that gets a meme for the conversation
def get_ai_meme(event,connection, chan):
    try:
        inputqueue = "; ".join(list(chatdeque[chan]))
        response = client.models.generate_content(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(system_instruction=sys_instruct_news),
        contents=f"{inputqueue}.  Find a meme for this conversation.  Respond with a link along with a sentence or two about the meme.",
        )
        if not response.text:
            print("*** Blank Response! ***")
            return
    except errors.APIError as e:
        print(e.code)
        print(e.message)
        connection.privmsg(event.target,"Meme routine error!")
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


if __name__ == "__main__":
    main()
