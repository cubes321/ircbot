import irc.client
import requests
import time
import json
from google import genai
from google.genai import types
with open('e:/ai/genai_api_key.txt') as file:
    api_key = file.read().strip()
client = genai.Client(api_key=api_key)

sys_instruct_anime="You are a haughty ojou-sama, the daughter of a rich and powerful family.  The request is of the format '[name]: [request]'. Limit your output to 450 characters per paragraph. The channel name is #anime"
sys_instruct_geeks="You are a haughty ojou-sama, the daughter of a rich and powerful family.  The request is of the format '[name]: [request]'. Limit your output to 450 characters. The channel name is #geeks"
sys_instruct_uk="You are a haughty ojou-sama, the daughter of a rich and powerful family. The request is of the format '[name]: [request]'. Limit your output to 450 characters. The channel name is #uk"
sys_instruct_england="You are a haughty ojou-sama, the daughter of a rich and powerful family.  The request is of the format '[name]: [request]'.  Limit your output to 450 characters.  The channel name is #england"
sys_instruct_init="Limit your output to 450 characters. You are a haughty ojou-sama, the daughter of a rich and powerful family. "

# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = "Ojousama"  # Bot's nickname
CHANNELS = ["#geeks", "#uk", "#anime", "#england"]  # Channel to join

#geeks channel
chatgeeks = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_geeks),
    )

chatanime = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_anime),
    )

chatengland = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_england),
    )

chatuk = client.chats.create(
        model="gemini-2.0-flash-thinking-exp",
        config=types.GenerateContentConfig(system_instruction=sys_instruct_uk),
    )

def on_connect(connection, event):
    for chan in CHANNELS:
       print("Joining channel: " + chan)
       connection.join(chan)
       if chan == "#uk":
           response = client.models.generate_content(
            model="gemini-2.0-flash-thinking-exp",
            config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
            contents="Create a suitable joining message for an IRC channel.  Mention that you can be called by using 'Ojousama' followed by a message.",
)
       if chan == "#england":
           response = client.models.generate_content(
            model="gemini-2.0-flash-thinking-exp",
            config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
            contents="Create a suitable joining message for an IRC channel.  Mention that you can be called by using 'Ojousama' followed by a message.",
)
       if chan == "#geeks":
           response = client.models.generate_content(
            model="gemini-2.0-flash-thinking-exp",
            config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
            contents="Create a suitable joining message for an IRC channel.  Mention that you can be called by using 'Ojousama' followed by a message.",
)
       if chan == "#anime":
           response = client.models.generate_content(
            model="gemini-2.0-flash-thinking-exp",
            config=types.GenerateContentConfig(system_instruction=sys_instruct_init),
            contents="Create a suitable joining message for an IRC channel.  Mention that you can be called by using 'Ojousama' followed by a message.",
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



def message(text):
    json_data = json.dumps({"body": text[:500]})
    headers = {"Content-Type": "application/json"}

    response = requests.post(BOT_API_URL, data=json_data, headers=headers)

    return response		

def on_message(connection, event):
    print(event.target + ":" + event.source.nick + ": " + event.arguments[0])
    inputtext = event.arguments[0][7:]
#    print(event.target + ":" + event.source.nick + ": " + inputtext)
#    inputtext = inputtext.lower()
    inputtext = event.source.nick + ": " + inputtext
    chan = event.target
    maidnick = event.arguments[0][:8].lower().strip()
    if event.arguments[0][:8].lower().strip() == "ojousama":
        if chan == "#geeks":
            response = chatgeeks.send_message(inputtext)
            para_text = response.text.splitlines()
            nonempty_para_text = [line for line in para_text if line.strip()]
            for paragraph in nonempty_para_text:
                result = paragraph.replace("\n"," ")
                result = paragraph.replace("\r"," ")
                output = paragraph[:450]
                print(output)
                count = len(chatgeeks._curated_history)
#                print(f"chatgeeks hist len: {chatgeeks._curated_history.count()}")
                print(f"chatgeeks hist len: {count}")
                connection.privmsg(event.target,output)
                time.sleep(1)


    if event.arguments[0][:8].lower().strip() == "ojousama":
        if chan == "#anime":
            response = chatanime.send_message(inputtext)
            para_text = response.text.splitlines()
            nonempty_para_text = [line for line in para_text if line.strip()]
            for paragraph in nonempty_para_text:
                result = paragraph.replace("\n"," ")
                result = paragraph.replace("\r"," ")
                output = paragraph[:450]
                print(output)
#                print(f"chatanime hist len: {chatanime._curated_history.count()}")
                count = len(chatanime._curated_history)
                print(f"chatanime hist len: {count}")
                connection.privmsg(event.target,output)
                time.sleep(1)


    if event.arguments[0][:8].lower().strip() == "ojousama":
        if chan == "#uk":
            response = chatuk.send_message(inputtext)
            para_text = response.text.splitlines()
            nonempty_para_text = [line for line in para_text if line.strip()]
            for paragraph in nonempty_para_text:
                result = paragraph.replace("\n"," ")
                result = paragraph.replace("\r"," ")
                output = paragraph[:450]
                print(output)
#                print(f"chatuk hist len: {chatuk._curated_history.count()}")
                count = len(chatuk._curated_history)
                print(f"chatuk hist len: {count}")
                connection.privmsg(event.target,output)
                time.sleep(1)

    if event.arguments[0][:8].lower().strip() == "ojousama":
        if chan == "#england":
            response = chatengland.send_message(inputtext)
            para_text = response.text.splitlines()
            nonempty_para_text = [line for line in para_text if line.strip()]
            for paragraph in nonempty_para_text:
                result = paragraph.replace("\n"," ")
                result = paragraph.replace("\r"," ")
                output = paragraph[:450]
                print(output)
#                print(f"chatuk hist len: {chatuk._curated_history.count()}")
                count = len(chatengland._curated_history)
                print(f"chatengland hist len: {count}")
                connection.privmsg(event.target,output)
                time.sleep(1)

if __name__ == "__main__":
    main()