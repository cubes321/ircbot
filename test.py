import irc.client
import requests
import time
import json
from google import genai
from google.genai import types
with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

sys_instruct_cubes="You are the prim and proper head maid of an english stately home.  You are multi-talented and very intelligent. The request is of the format '[name]: [request]'. Reply with the name of the person talking to you is preferred. Limit your output to 450 characters per paragraph and at most 2 paragraphs. The channel name is #geeks"
sys_instruct_init="Limit your output to 450 characters. You are the prim and proper head maid of an english stately home.  You are multi-talented and very intelligent. "

# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = "Testbot"  # Bot's nickname
CHANNELS = ["#cubes"]  # Channel to join

#geeks channel
chatcubes = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_cubes),
    )

def on_connect(connection, event):
    for chan in CHANNELS:
       print("Joining channel: " + chan)
       connection.join(chan)
       response = client.models.generate_content(
            model="gemini-2.0-flash-thinking-exp",
            config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
            contents="Create a suitable joining message for an IRC channel.  Mention that you can be called by using 'MaidBot' followed by a message.",
)
       result = response.text
       result = result.replace("\n"," ")
       result = result.replace("\r"," ")
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
    print(event.target + ":" + event.source.nick + ": " + event.arguments[0])
    inputtext = event.arguments[0][7:]
#    print(event.target + ":" + event.source.nick + ": " + inputtext)
#    inputtext = inputtext.lower()
    inputtext = event.source.nick + ": " + inputtext
    chan = event.target
    maidnick = event.arguments[0][:7].lower().strip()
    if event.arguments[0][:7].lower().strip() == "maidbot":
        if chan == "#cubes":
            response = chatcubes.send_message(inputtext)
            para_text = response.text.splitlines()
            nonempty_para_text = [line for line in para_text if line.strip()]
            for paragraph in nonempty_para_text:
                result = paragraph.replace("\n"," ")
                result = paragraph.replace("\r"," ")
                output = paragraph[:450]
                print(output)
                count = len(chatcubes._curated_history)
#                print(f"chatgeeks hist len: {chatgeeks._curated_history.count()}")
                print(f"chatgeeks hist len: {count}")
                connection.privmsg(event.target,output)
                time.sleep(1)

if __name__ == "__main__":
    main()