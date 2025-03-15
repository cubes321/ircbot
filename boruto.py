import irc.client
import requests
import time
import json

endpoint_url = "http://localhost:1234/api/v0/chat/completions"


# IRC Server details
SERVER = "irc.quakenet.org"  # Change to your preferred IRC server
PORT = 6667  # Standard IRC port
NICK = "CafeBot"  # Bot's nickname
CHANNELS = ["#anime"]  # Channel to join


def on_connect(connection, event):
    for chan in CHANNELS:
       print("Joining channel: " + chan)
       connection.join(chan)
       connection.privmsg(chan, "Hello, world!  The Cafe is now open.  Use !cafe to order")


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
    bword = event.arguments[0].find("boruto")
    if bword > 0:
#    if event.arguments[0][:6].strip() == "!cage":	
         print(event.arguments[0])
         joined_list = event.arguments[0][6:]
         payload = {
              "messages": [
#                    { "role": "system", "content": "Be concise with your answers." },
                    { "role": "system", "content": "You serve as a maid in a japanese maid cafe.  A boruto is a fictional menu item in your cafe.  You also sell all other foodstuffs  A person called Fanen has to pay in cash and has no credit. Answer concisely in the style of an employee in a japanese maid cafe" },
                    { "role": "user", "content": joined_list }
              ],
              "temperature": 0.7,
              "max_tokens": 400,
              "stream": False
}
         headers = {"Content-Type": "application/json"}
         response = requests.post(endpoint_url, json=payload, headers=headers)
         if response.status_code == 200:
           json_data = json.loads(response.text)
           result = json_data["choices"][0]["message"]["content"]
           result = result.replace("\n"," ")
           result = result.replace("\r"," ")
#           output = result[:450] + "..."
           output = result[:450]
#           print(result[:500])
#           connection.privmsg(event.target,result[:500])
           print(output)
           connection.privmsg(event.target,output)
    if event.arguments[0][:6].strip() == "!cafe":	
         print(event.arguments[0])
         joined_list = event.arguments[0][6:]
         payload = {
              "messages": [
#                    { "role": "system", "content": "Be concise with your answers." },
                    { "role": "system", "content": "You serve in a cafe.  Your product is a foodstuff called a Boruto which is only available in a deluxe meal package" },
                    { "role": "user", "content": joined_list }
              ],
              "temperature": 0.7,
              "max_tokens": 400,
              "stream": False
}
         headers = {"Content-Type": "application/json"}
         response = requests.post(endpoint_url, json=payload, headers=headers)
         if response.status_code == 200:
           json_data = json.loads(response.text)
           result = json_data["choices"][0]["message"]["content"]
           result = result.replace("\n"," ")
           result = result.replace("\r"," ")
#           output = result[:450] + "..."
           output = result[:450]
#           print(result[:500])
#           connection.privmsg(event.target,result[:500])
           print(output)
           connection.privmsg(event.target,output)
		 
		 
if __name__ == "__main__":
    main()