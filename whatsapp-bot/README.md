# Brajawali WhatsApp Bot

Run a WhatsApp bot **on your own number** that translates Assamese to Brajawali on demand.

```
You (in any WhatsApp chat) ──▶  /braja মই তোমাক ভাল পাওঁ
Bot (also you, replying to yourself or a friend) ──▶  *মঞি তোহাক ভল্ল পাও*
```

No Twilio, no servers, no extra phone number. Uses your real WhatsApp account via WhatsApp Web's protocol (the same way `web.whatsapp.com` works).

## Requirements

- **Node.js 18+**
- **WhatsApp on your phone** (you'll scan a QR code once)
- **Mac/PC running** while you want to use the bot

## Install (once)

```bash
cd ~/.claude/skills/brajawali/whatsapp-bot
npm install
```

This downloads ~200 MB (whatsapp-web.js bundles a Chromium binary it controls headlessly — that's the WhatsApp Web client).

## Run

```bash
npm start
```

First run: a QR code prints in the terminal.

1. On your phone open WhatsApp → **Settings → Linked Devices → Link a Device**
2. Scan the QR code in your terminal
3. The bot says `✅ Bot is ready.`

The session is persisted in `.wwebjs_auth/` so you don't need to scan again.

## Use

In **any WhatsApp chat** (including your own chat-with-yourself, a group, or a DM with a friend), type:

```
/braja মই তোমাক ভাল পাওঁ
```

The bot replies with:

```
*মঞি তোহাক ভল্ল পাও*

input: মই তোমাক ভাল পাওঁ

Word-by-word:
  ✓ মই → মঞি
  ✓ তোমাক → তোহাক
  ✓ ভাল → ভল্ল
  ✓ পাওঁ → পাও
```

Roman input also works:

```
/braja moi tumar logot ahisilo
```

Help:

```
/braja-help
```

## Permissions

By default the bot **only responds to messages you sent yourself**. This way friends can't accidentally trigger `/braja` if they happen to type that in a chat with you.

To let anyone messaging you also use `/braja`:

```bash
ALLOW_OTHERS=1 npm start
```

## How it works

```
WhatsApp message
       │
       ▼
whatsapp-web.js (controls a headless Chromium running web.whatsapp.com)
       │
       ▼
Sees /braja <text> → spawns ./translate "<text>" subprocess
       │
       ▼
translate_v2.py runs (Python, NLP-backed)
       │
       ▼
JSON output formatted as WhatsApp markdown
       │
       ▼
Bot replies into the same chat
```

## Stop / restart / logout

- **Stop:** Ctrl-C in the terminal.
- **Restart:** `npm start` — session is remembered.
- **Logout / re-pair to a different phone:** `npm run logout` then `npm start`.

## Run forever (background)

To keep it running after you close the terminal:

```bash
# Option 1: nohup
nohup npm start > bot.log 2>&1 &

# Option 2: pm2 (process manager)
npm install -g pm2
pm2 start bot.js --name brajawali-bot
pm2 save
pm2 startup            # auto-start on Mac boot
```

## Caveats

- **Your Mac must be running** (and online) for the bot to respond.
- **WhatsApp ToS gray area:** WhatsApp doesn't officially endorse third-party clients, but this is the same protocol your laptop's WhatsApp Web uses. For low-volume personal use the risk is negligible. WhatsApp would typically just unpair the device, not ban your number.
- **One linked device limit:** WhatsApp allows up to 4 linked devices on a phone. This bot uses one slot.
- **First message after a long quiet period** can take 5–10 seconds while the bot wakes up; subsequent messages are instant.

## Troubleshooting

| Problem | Fix |
|---|---|
| `npm install` fails on Chromium | `npm install --unsafe-perm` or pre-install: `brew install chromium` |
| QR code doesn't render in terminal | Make terminal window wider; or pipe to a file: `npm start \| tee qr.txt` |
| `Auth failed` | `npm run logout` then `npm start` |
| `/braja` ignored | Make sure you typed it from your own number (or set `ALLOW_OTHERS=1`) |
| Replies are slow | First message wakes Python venv — subsequent ones are <1s |
| Translator errors | Test directly: `~/.claude/skills/brajawali/translate "test"` |
