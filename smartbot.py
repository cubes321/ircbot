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
import os
import argparse  # <-- already imported

# handle commandline
default_config = os.path.splitext(os.path.basename(sys.argv[0]))[0] + ".ini"
default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), default_config)

parser = argparse.ArgumentParser(
    description="AI IRC SmartBot",
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False  # We'll handle help manually
)
parser.add_argument('-c', '--config', type=str, help='Path to config file')
parser.add_argument('--show-config', action='store_true', help='Show example config file and exit')
parser.add_argument('-s', '--setting', action='append', help='Override config setting, e.g. -s General.nick=MyBot. Can be used multiple times.')
parser.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')
parser.add_argument('-k', '--keyfile', type=str, help='Path to Google GenAI API key file, or the API key itself. If not supplied, will look for <scriptname>.key or ../../genai_api_key.txt')
parser.add_argument('-d', '--databasefile', type=str, help='Path to JSON database file (overrides config and default detection)')

args, unknown = parser.parse_known_args()

# Show help if -h, --help, or /? is present
if args.help or '/?' in sys.argv:
    print(f"""
AI IRC SmartBot - Command Line Options

Usage:
  python {os.path.basename(sys.argv[0])} [options]

Options:
  -c, --config <file>         Path to config file (INI format).
  --show-config               Show an example config file and exit.
  -s, --setting <setting>     Override config setting, e.g. -s General.nick=MyBot.
                              Can be used multiple times.
  -k, --keyfile <file/key>    Path to Google GenAI API key file, or the API key itself.
                              If not supplied, will look for <scriptname>.key or ../../genai_api_key.txt
  -d, --databasefile <file>   Path to JSON database file (overrides config and default detection)
  -h, --help, /?              Show this help message and exit.

Examples:
  python {os.path.basename(sys.argv[0])} --show-config
  python {os.path.basename(sys.argv[0])} -c mybot.ini
  python {os.path.basename(sys.argv[0])} -s General.nick=DaveBot -s IRCServer.port=6697
  python {os.path.basename(sys.argv[0])} -k mykeyfile.txt
  python {os.path.basename(sys.argv[0])} -k AIzaSy...
  python {os.path.basename(sys.argv[0])} -d mydata.json

If no config file is supplied, the bot will look for a default INI file
named after the script (e.g., ai-smartbot.ini) in the script directory.
If no API key is supplied, the bot will look for a file named after the script (e.g., ai-smartbot.key)
in the script directory, or ../../genai_api_key.txt as a fallback.
If no database file is supplied, the bot will look for a file named after the script (e.g., ai-smartbot.json)
in the script directory.

""")
    sys.exit(0)

# Determine which config file to use
if args.config:
    config_file_to_use = args.config
elif os.path.isfile(default_config_path):
    config_file_to_use = default_config_path
else:
    config_file_to_use = None  # Allow running with only --setting overrides

def parse_settings(settings_list):
    """
    Parse a list of -s/--setting arguments into a dict of {section: {key: value}}
    Example: ['General.nick=MyBot', 'IRCServer.port=6667']
    """
    result = {}
    if not settings_list:
        return result
    for item in settings_list:
        if '=' not in item or '.' not in item:
            print(f"Invalid --setting format: {item}. Use Section.key=value")
            sys.exit(1)
        section_key, value = item.split('=', 1)
        section, key = section_key.split('.', 1)
        if section not in result:
            result[section] = {}
        result[section][key] = value
    return result

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

# Load the API key from a file or direct string
def load_api_key(keyfile_arg=None):
    # 1. If --keyfile is supplied, use it as a file or direct key
    if keyfile_arg:
        if os.path.isfile(keyfile_arg):
            with open(keyfile_arg, 'r') as f:
                print(f"Loaded API key from file: {keyfile_arg}")
                return f.read().strip()
        elif keyfile_arg.strip().startswith("AIza") and len(keyfile_arg.strip()) > 30:
            print("Loaded API key directly from command line argument.")
            return keyfile_arg.strip()
        else:
            print("Error: --keyfile must be a valid file path or a valid API key string.")
            sys.exit(1)
    # 2. Check for <scriptname>.key in script directory
    script_key = os.path.splitext(os.path.basename(sys.argv[0]))[0] + ".key"
    script_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_key)
    if os.path.isfile(script_key_path):
        with open(script_key_path, 'r') as f:
            print(f"Loaded API key from default key file: {script_key_path}")
            return f.read().strip()
    # 3. Fallback to ../../genai_api_key.txt
    default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../genai_api_key.txt'))
    if os.path.isfile(default_path):
        with open(default_path, 'r') as f:
            print(f"Loaded API key from fallback file: {default_path}")
            return f.read().strip()
    print("Error: No API key provided and no default key file found. Use -k/--keyfile or place a .key file next to the script.")
    sys.exit(1)

api_key = load_api_key(args.keyfile)
client = genai.Client(api_key=api_key)

# IRC Server details
# load server details, nick, channels to join and system prompt from config file
def load_config(config_file=config_file_to_use, override_settings=None):
    config = configparser.ConfigParser()
    if config_file:
        config.read(config_file)
    # Apply overrides from --setting
    if override_settings:
        for section, kv in override_settings.items():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in kv.items():
                config.set(section, key, value)

    # --- PATCH: Default to scriptname.json if database_file missing ---
    if not config.has_section('Specifics'):
        config.add_section('Specifics')
    # If --databasefile is supplied, use it (overrides everything)
    if args.databasefile:
        config.set('Specifics', 'database_file', args.databasefile)
        print(f"Database file set from command line: {args.databasefile}")
    elif not config.has_option('Specifics', 'database_file') or not config.get('Specifics', 'database_file'):
        script_json = os.path.splitext(os.path.basename(sys.argv[0]))[0] + ".json"
        script_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_json)
        if os.path.isfile(script_json_path):
            config.set('Specifics', 'database_file', script_json_path)
            print(f"Database file not set in config, using: {script_json_path}")

    # Now, try to extract required settings, error if missing
    try:
        server_info = {
            'server': config['IRCServer']['server'],
            'port': int(config['IRCServer']['port'])
        }
        general_info = {
            'nick': config['General']['nick']
        }
        specifics_info = {
            'sysprompt': config['Specifics']['sysprompt'],
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
    except KeyError as e:
        print(f"Error: Missing required configuration key: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

# Load the configuration file, with possible overrides
override_settings = parse_settings(args.setting)
if not config_file_to_use and not override_settings:
    print(f"Error: No config file specified and no --setting overrides provided.")
    sys.exit(1)
config = load_config(config_file=config_file_to_use, override_settings=override_settings)

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
