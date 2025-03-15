import irc.client
import requests
import time
import json

endpoint_url = "http://localhost:1234/api/v0/chat/completions"


# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = "CubesBot"  # Bot's nickname
CHANNEL = "#nerds"  # Channel to join


def on_connect(connection, event):
    connection.join(CHANNEL)
    connection.privmsg(CHANNEL, "Hello, world!  Use !cubes <message> to use me")

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

    return response		

def on_message(connection, event):
    print(event.arguments[0])
    if event.arguments[0][:6].strip() == "!cubes":	
#         connection.privmsg(CHANNEL, "How can i help you?")
         joined_list = event.arguments[0][7:]
#         print(event.arguments[0])
#         connection.privmsg(CHANNEL,"in the if statement")
         payload = {
#		      "model": "llama-3.2-3b-instruct",
              "messages": [
                    { "role": "system", "content": "Be concise with your answers." },
#                    { "role": "user", "content": "Describe the difference between a nerd and a geek" }
                    { "role": "user", "content": joined_list }
              ],
              "temperature": 0.7,
              "max_tokens": 100,
              "stream": False
}
         headers = {"Content-Type": "application/json"}
#    response = requests.post(endpoint_url, params=params, headers=headers)
         response = requests.post(endpoint_url, json=payload, headers=headers)
         if response.status_code == 200:
           json_data = json.loads(response.text)
           result = json_data["choices"][0]["message"]["content"]
           result = result.replace("\n"," ")
           result = result.replace("\r"," ")
           print(result)
           connection.privmsg(CHANNEL,result[:505])
#         connection.privmsg(CHANNEL, json_data["choices"][0]["message"]["content"])
#         print("Response:", response.json())
		 
		 
if __name__ == "__main__":
    main()