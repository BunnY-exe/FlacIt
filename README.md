```
    _____ _            ___ _
   |  ___| | __ _  ___|_ _| |_
   | |_  | |/ _` |/ __|| || __|
   |  _| | | (_| | (__ | || |_
   |_|   |_|\__,_|\___|___|\__|
```

**Search any song from your terminal. Get a FLAC. No accounts. No nonsense.**

![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-5.0+-4EAA25?logo=gnubash&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)
![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange?logo=linux&logoColor=white)

---

## What is this?

FlacIt is a terminal tool that lets you search for any song by name and download it as a lossless FLAC file — straight from the command line. Type `newsong "Bohemian Rhapsody"`, pick from the results, and the FLAC lands in your music folder. That's it.

Under the hood, it talks to Telegram's `@deezload2bot` using Telethon (an MTProto client for Python). When you search, FlacIt fires an inline query — the same mechanism that runs when you type `@deezload2bot song name` in Telegram's message bar. The bot returns results, you pick one, and FlacIt clicks it into your bot chat. When the FLAC document arrives, it hands the message ID off to `tdl` for fast parallel downloading.

No Spotify Premium. No broken third-party APIs. No rate limits to dance around. The bot does the heavy lifting; FlacIt just gives you a clean terminal interface to drive it.

---

## Features

- 🔍 **Smart search** — powered by @deezload2bot's inline query, returns up to 10 results instantly
- 🎯 **Pick your version** — choose exactly which artist/album version you want
- ⚡ **Fast downloads** — uses `tdl` for parallel chunk downloading, not slow single-stream
- 🔗 **Direct link mode** — already have a Spotify or Deezer link? Use `newsong -l "https://..."` to skip search entirely
- 📁 **Clean filenames** — saves as `Artist - Song.flac` directly to your music folder
- 🔒 **Zero API keys** — no Spotify account, no developer portal, nothing to register
- 🖥️ **Beautiful terminal UI** — live progress bar, braille spinner, colored output

---

## Requirements

- **Linux** (tested on Ubuntu/Debian)
- **Python 3.8+**
- **pip** (Python package manager)
- **tdl** (Telegram Downloader CLI)
- **A Telegram account** (free)
- **git** (to clone)

---

## Setup Guide

### Step 1 — Install system dependencies

```bash
# Update your package list so apt knows about the latest versions
sudo apt update

# Install Python 3 and pip (Python's package manager) if you don't have them
sudo apt install python3 python3-pip git -y
```

### Step 2 — Install tdl (the fast Telegram downloader)

tdl is a command-line tool that downloads files from Telegram using parallel connections — much faster than downloading one chunk at a time.

```bash
# Download and install the tdl binary
curl -sSL https://docs.iyear.me/tdl/install.sh | sudo bash
```

### Step 3 — Install Telethon (Python library for Telegram)

```bash
# Install the Telethon library — this lets FlacIt talk to Telegram on your behalf
pip install telethon --break-system-packages
```

### Step 4 — Clone FlacIt

```bash
# Download the FlacIt project to your computer
git clone https://github.com/BunnY-exe/FlacIt.git

# Go into the project folder
cd FlacIt
```

### Step 5 — Set your music folder

Open `newsong` in any text editor you have — nano, gedit, mousepad, whatever works. Find this line near the top:

```bash
OUTPUT_DIR="$HOME/off-music"
```

Change `off-music` to whatever folder name you want your FLACs saved in. For example `Music`, `FLAC`, or just leave it as `off-music`. The folder will be created automatically the first time you download something.

### Step 6 — Install FlacIt

```bash
# Create the local bin folder if it doesn't exist (this is where user scripts live)
mkdir -p ~/.local/bin

# Copy the main script to that folder
cp newsong ~/.local/bin/newsong

# Make it executable (so Linux lets you run it)
chmod +x ~/.local/bin/newsong

# Copy the Python helper to your home folder
cp newsong_dl.py ~/newsong_dl.py

# Add ~/.local/bin to your PATH so you can run 'newsong' from anywhere
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Reload your shell config to apply the PATH change immediately
source ~/.bashrc
```

### Step 7 — Log in to tdl

The fastest way is to copy your existing Telegram Desktop session:

```bash
# Point tdl to your Telegram Desktop data directory (one-time setup)
tdl login -d ~/.local/share/TelegramDesktop/tdata
```

> **Note:** If Telegram was installed via Flatpak, use this path instead:
> ```bash
> tdl login -d ~/.var/app/org.telegram.desktop/data/TelegramDesktop/tdata
> ```
> If neither path exists on your system, just run `tdl login` by itself — it will authenticate using a standard login code sent to your Telegram app.

### Step 8 — ⚠️ Important: Interact with @deezload2bot once manually

> ⚠️ **Before using FlacIt, you MUST open Telegram and start a conversation with @deezload2bot manually.**
>
> Search for `@deezload2bot` in Telegram, open the chat, and press **Start**. The bot will ask you to join their channel — **you must join it**. This is a one-time step. If you skip this, FlacIt will time out waiting for a response and nothing will download.

### Step 9 — First run (Telegram auth)

```bash
# Run FlacIt for the first time — it will ask for your Telegram phone number
newsong "test"
```

The first time you run it, Telethon will ask for your phone number and send a login code to your Telegram app. Enter it when prompted. This only happens once — your session is saved permanently after that.

---

## Usage

**Basic search:**

```bash
newsong "O Rangrez"
newsong "Bohemian Rhapsody"
newsong "we dont talk anymore"
```

**Direct link mode** — when you already have the Spotify or Deezer link:

```bash
newsong -l "https://open.spotify.com/track/7tFiyTwD0nx5a1eklYtX2J"
newsong -l "https://www.deezer.com/track/3135556"
```

Sometimes the inline search returns the wrong version — a remix, a live recording, a different album cut. If that happens, find the exact track on Spotify or Deezer, copy the share link, and use `-l` to download that specific version directly. The bot resolves the link and sends the correct FLAC.

---

## ⏳ Note on Download Speed

> After you confirm your selection and the download begins, **tdl may take 30–60 seconds before the progress bar starts moving**. This is normal — tdl is negotiating the download from Telegram's servers. Don't close the terminal. Just wait. Once it starts, it's fast.

---

## How It Works (Technical)

For the curious — here's the full pipeline:

1. FlacIt uses **Telethon** (a Python MTProto client) to run an inline query against `@deezload2bot` — the same query that fires when you type `@deezload2bot song name` in Telegram's message bar
2. The bot returns up to 50 results; FlacIt shows you the top 10 with track name and artist
3. You pick a number; FlacIt calls `results[idx].click()` to send that track into your bot chat — exactly as if you tapped it on your phone
4. The bot processes it and delivers a FLAC document to the chat
5. FlacIt detects the incoming file, extracts its message ID and file size, and hands it to **tdl** — which downloads using parallel connections at full speed
6. While tdl runs, a live progress bar polls the growing file on disk and shows you `████████░░░░ 42% (11.2 / 27.9 MB)` in real time
7. The file lands in your music folder named `Artist - Song.flac`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: newsong` | Run `source ~/.bashrc` or open a new terminal |
| Stuck at "Waiting for @deezload2bot..." | Open Telegram, find @deezload2bot, press Start and join their channel |
| Progress bar doesn't move for a minute | Normal — wait 30–60s for tdl to start |
| `BotResponseTimeoutError` | Bot is busy, FlacIt retries automatically up to 3 times |
| First run asks for phone number | Expected — enter your Telegram phone number and the code sent to your app |
| Wrong song downloaded | Use `newsong -l "spotify-link"` to specify the exact track |

---

## Contributing

FlacIt is a personal tool that grew into something shareable. If you hit a bug, open an issue with the exact error output. If you want to add something — a queue mode, playlist support, album downloads — PRs are open. Keep it simple, keep it terminal-native.

---

## License

MIT — do whatever you want with it.

---

## Acknowledgements

- [@deezload2bot](https://t.me/deezload2bot) — the bot that makes this all possible
- [Telethon](https://github.com/LonamiWebs/Telethon) — MTProto Python client
- [tdl](https://github.com/iyear/tdl) — fast Telegram downloader
