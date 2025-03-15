import irc.client
import requests
import time
import json
from google import genai
from google.genai import types



with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

chat_history = [
     {"role": "user", "content": "Hello, are you there?"},
    {"role": "model", "content": "Yes, I am here and ready to assist you."},
    {"role": "user", "content": "What can you help me with?"},
]

model = genai.Model("gemini-2.0-flash")
sys_instruct="You are a big Weeb who loves Naruto.  You are talking on an anime related IRC channel.  Fanen hates Naruto.  You like Frontslash. Don't use emojis. Limit your output to 450 characters"
sys_instruct2="You are a maid in a japanese maid cafe.  You serve many items including a new foodstuff called a Boruto. The request is of the format 'name: request'. Reply with the name of the person talking to you is preferred. Koneko is your rival maid. Limit your output to 450 characters"

# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = "MaidBot"  # Bot's nickname
CHANNELS = ["#cubes"]  # Channel to join




chat = model.start_chat(history=chat_history)


def on_connect(connection, event):
    for chan in CHANNELS:
       print("Joining channel: " + chan)
       connection.join(chan)

def main():
    reactor = irc.client.Reactor()
    try:
        c = reactor.server().connect(SERVER, PORT, NICK)
        c.add_global_handler("welcome", on_connect)
        c.add_global_handler("pubmsg", on_message)
        reactor.process_forever()
    except irc.client.ServerConnectionError:
        print("Connection error")


def message(text):
    json_data = json.dumps({"body": text[:500]})
    headers = {"Content-Type": "application/json"}

    response = requests.post(BOT_API_URL, data=json_data, headers=headers)

    return response		


def on_message(connection, event):
    inputtext = event.arguments[0][6:]
    print(event.source.nick + " " + inputtext)
    inputtext = inputtext.lower()
    inputtext = event.source.nick + ": " + inputtext
    if event.arguments[0][:6].strip() == "!cafe":

#        response = chat.send_message(inputtext, history=chat.history)
        chat_history.append({"user": inputtext})
        response = chat_session.send_message(message=inputtext, history=chat_history)
        print(response.text)
        result = response.text
        result = result.replace("\n"," ")
        result = result.replace("\r"," ")
        output = result[:450]
        print(output)
        connection.privmsg(event.target,output) 
        if event.arguments[0][:6].strip() == "!cafe":
            return


if __name__ == "__main__":
    main()