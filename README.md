# SmartBot - An AI Powered IRC Bot

## Description

SmartBot is a Python-based IRC bot that uses Google's Generative AI (Gemini models) to interact with users in IRC channels. It can understand natural language, respond to queries, and perform specific actions based on commands. The bot is designed to be configurable for different IRC servers, nicknames, channels, and AI personas.

## Features

*   Connects to IRC servers and joins multiple channels.
*   Integrates with Google Generative AI for intelligent responses.
*   Handles direct messages and specific commands.
*   **General Conversation:** Responds to messages addressed to its nickname.
*   **News Updates (`!news`):** Fetches and shares the latest news.
*   **Art Critique (`!art <image_url>`):** Provides an AI-generated art critique for a given JPG image URL.
*   **YouTube Video Summarization (`!yt <video_url>`):** Summarizes the content of a YouTube video.
*   **Anime YouTube Video Opinion (`!animeyt <video_url>`):** Shares an AI opinion on an anime-related YouTube video.
*   **Meme Finder (`!meme`):** Suggests a relevant meme based on the recent channel conversation.
*   **Randomized Responses:** Occasionally responds to general channel chat to keep engagement.
*   Configurable system prompt to define the bot's personality.
*   Output formatting to prevent IRC flooding (splits long messages into manageable chunks).

## Requirements

### Software
*   Python 3.x
*   The following Python libraries (can be installed via `pip`):
    *   `irc`
    *   `requests`
    *   `google-generativeai`
    *   `configparser`

    You can create a `requirements.txt` file with the following content:
    ```txt
    irc
    requests
    google-generativeai
    configparser
    ```
    And install them using: `pip install -r requirements.txt`

### API Keys
*   **Google Generative AI API Key:**
    *   You need an API key from Google AI Studio (or Google Cloud AI Platform).
    *   This key must be saved in a plain text file. The script defaults to `e:/ai/genai_api_key.txt`, but this path is hardcoded in `smartbot.py` and can be modified if you store the key file elsewhere.

### Configuration File
*   The bot requires a configuration file (e.g., `config.ini`) to be specified as a command-line argument when running the script.
*   This file contains details about the IRC server, bot identity, and AI behavior.

## Setup & Installation

1.  **Clone or download `smartbot.py`.**
2.  **Install Python dependencies:**
    ```bash
    pip install irc requests google-generativeai configparser
    ```
    Alternatively, if you created `requirements.txt` as shown above:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up Google Generative AI API Key:**
    *   Obtain your API key from [Google AI Studio](https://aistudio.google.com/) or your Google Cloud project.
    *   Create a file (e.g., `genai_api_key.txt`) and paste your API key into it.
    *   The script, by default, looks for this file at `e:/ai/genai_api_key.txt`. If you place it in a different location, you **must** update the following line in `smartbot.py` accordingly:
        ```python
        with open('YOUR/ACTUAL/PATH/TO/genai_api_key.txt') as file:
            api_key = file.read().strip()
        ```

4.  **Create a Configuration File:**
    Create a file named `config.ini` (or any other name, but you'll need to provide it when running the bot). Populate it with the following structure:

    ```ini
    [IRCServer]
    server = your.irc.server.com
    port = 6667

    [General]
    nick = SmartBotNick
    # Channels should be a comma-separated list.
    # Examples of valid formats:
    # channels = ['#channel1', '#channel2']
    # channels = #channelone, #channeltwo
    # channels = '#channelX',#channelY
    channels = ['#yourchannel1', '#anotherchannel']

    [Specifics]
    # This prompt defines the bot's personality and how it should behave.
    sysprompt = a helpful and witty AI assistant
    ```
    *   Replace `your.irc.server.com` with the actual IRC server address.
    *   Set `port` if it's different from the default (6667 for non-SSL, 6697 for SSL - note: SSL is not explicitly handled in the current script version).
    *   Choose a `nick` for your bot.
    *   List the `channels` the bot should join.
    *   Define the `sysprompt` to give your bot a unique character.

## Running the Bot

Execute the script from your terminal, providing the path to your configuration file as the first argument:

```bash
python smartbot.py path/to/your/config.ini
```

For example, if your config file is named `config.ini` and is in the same directory as `smartbot.py`:

```bash
python smartbot.py config.ini
```

The bot will then connect to the specified IRC server and join the channels.

## Commands

To interact with the bot, type messages in the IRC channel. If a message **starts with the bot's nickname**, it will be processed as a direct query or command. For specific commands like `!news`, `!art`, etc., these should follow the nickname.

*   **General Queries:**
    *   `<BotNick>: <your question or message>`
    *   Example: `SmartBotNick: What's the weather like today?`

*   **`!news`:**
    *   `<BotNick>: !news`
    *   The bot will fetch and display current news headlines.

*   **`!art <image_url>`:**
    *   `<BotNick>: !art https://example.com/path/to/yourimage.jpg`
    *   The bot will provide an art critique of the linked JPG image.

*   **`!yt <video_url>`:**
    *   `<BotNick>: !yt https://www.youtube.com/watch?v=yourvideoid`
    *   The bot will summarize the provided YouTube video.

*   **`!animeyt <video_url>`:**
    *   `<BotNick>: !animeyt https://www.youtube.com/watch?v=animevideoid`
    *   The bot will give its opinion on the provided anime-related YouTube video.

*   **`!meme`:**
    *   `<BotNick>: !meme`
    *   The bot will analyze the last 10 messages in the channel and try to find a relevant meme, responding with a link and a short description.

## How it Works

SmartBot uses the `irc` library to handle IRC protocol communication. When a message is received, it's processed to determine if it's a command or a general query for the bot.

For AI interactions:
1.  User input (and sometimes recent conversation history or external content like web pages/images) is formatted.
2.  A system instruction (defined in `config.ini` as `sysprompt` and further specialized for certain tasks) guides the AI's response style and constraints.
3.  The request is sent to the Google Generative AI API (using Gemini models).
4.  The AI's response is received, cleaned (line breaks removed), split into manageable paragraphs (max 450 characters each), and sent to the IRC channel with a slight delay between paragraphs to prevent flooding.

The bot maintains a short history (deque of 10 messages) for each channel to provide context for features like `!meme` and random interjections.

## TODO / Future Improvements

*   The script contains a `TODO`: `re-write fire on specific word routine to fire using words taken from config file`. This suggests an enhancement to trigger bot responses based on configurable keywords found in messages, not just when addressed by its nickname or a specific command.
*   Error handling for network issues or API outages could be more robust.
*   Support for SSL IRC connections.
*   More sophisticated context management for AI conversations.
*   Additional commands and AI capabilities.
