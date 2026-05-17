# WhatsApp deployment

Get the Brajawali translator running as a WhatsApp contact you can message from your phone. ~15 minutes, **$0/month**.

## How it works

```
You (phone) ──msg──▶ Twilio sandbox ──webhook──▶ Render.com (Flask)
                                                         │
                                                         ▼
                                                    translate_v2.py
                                                         │
You (phone) ◀──reply──── Twilio sandbox ◀──TwiML─────────┘
```

You'll have a WhatsApp contact called `+1 415-523-8886` (Twilio's sandbox number). Message it any Assamese sentence; it replies with the Brajawali rendering.

---

## Setup (15 min)

### 1. Sign up for Twilio (5 min)

1. Go to https://www.twilio.com/try-twilio and create a free account.
2. In the console, navigate to **Messaging → Try it out → Send a WhatsApp message**.
3. You'll see a sandbox number (e.g. `+1 415 523 8886`) and a "join code" like `join purple-elephant`.
4. From your phone's WhatsApp, send the join code as a message to that number. Twilio will confirm: *"Twilio Sandbox: ✅ You're all set!"*

Now you're connected to the sandbox. You can already chat with it (it'll just echo for now).

### 2. Deploy the bot to Render (5 min)

1. Go to https://render.com and sign up (free tier, GitHub login).
2. Click **New +** → **Blueprint** → connect your GitHub account → select `KewangZhili/brajawali`.
3. Render reads `render.yaml` and provisions the service automatically.
4. Wait ~3 minutes for the first build. You'll get a URL like `https://brajawali-bot.onrender.com`.
5. Test it: open `https://brajawali-bot.onrender.com/` in your browser. Should say `Brajawali bot — alive`.

### 3. Wire Twilio → Render (2 min)

1. Back in Twilio: **Messaging → Settings → WhatsApp sandbox settings**.
2. In the field *"When a message comes in"*, paste:
   ```
   https://brajawali-bot.onrender.com/whatsapp
   ```
3. Set the dropdown next to it to **HTTP POST**.
4. Click **Save**.

### 4. Test it (30 seconds)

On your phone, open WhatsApp → the chat with Twilio's sandbox → type:

```
মই তোমাক ভাল পাওঁ
```

You should get back:

```
*মঞি তোহাক ভল্ল পাও*

_(input: মই তোমাক ভাল পাওঁ)_

Word-by-word:
  ✓ মই → মঞি
  ✓ তোমাক → তোহাক
  ✓ ভাল → ভল্ল
  ✓ পাওঁ → পাও
```

That's it. Talk to Brajawali Bot from your phone.

---

## Things to know

### Sandbox limits

- The Twilio sandbox is **free forever** but has limits: ~80 messages/day, only people who joined with the code can talk to it, and there's a "this is a sandbox" prefix on outbound messages.
- For personal use this is fine. If you want a real branded WhatsApp business number with your own name, you upgrade to Twilio's paid WhatsApp Business API (~$0.005/msg + display name approval).

### Render free tier

- Sleeps after 15 min of inactivity → first message after a sleep takes ~30s to wake up. Subsequent messages are instant.
- 512 MB RAM, 0.1 CPU — plenty for this workload.
- 750 hours/month free.

### Sandbox session expires

- Twilio's sandbox session lasts 72 hours from your last message. If you stop using it for 3 days, you re-send the join code.

---

## Local testing

You can test the webhook locally before deploying:

```bash
cd ~/.claude/skills/brajawali
.venv/bin/pip install flask
.venv/bin/python server/app.py
```

Then in another terminal:

```bash
curl -X POST -d "Body=মই তোমাক ভাল পাওঁ" http://localhost:8000/whatsapp
```

You should see the TwiML response.

To expose your local server publicly for Twilio (instead of Render), use ngrok:

```bash
brew install ngrok
ngrok http 8000
```

Use the resulting `https://xxxx.ngrok.io/whatsapp` as your Twilio webhook URL.

---

## Cost ceiling

- **Free for personal use.** Twilio sandbox is gratis. Render free tier is gratis.
- If you outgrow the sandbox: production WhatsApp Business via Twilio is **$0.005 per outbound message** + a one-time number activation fee (~$5).
- Render free tier covers ~750 hours/month of always-on; that's $0. If you upgrade for no-sleep, it's $7/month.

## Troubleshooting

| Symptom | Fix |
|---|---|
| First message after a quiet period takes 30s | Render free tier woke up; subsequent messages are fast. Or pay $7/mo for always-on. |
| `❌ error: ImportError: indic-nlp-library` | Render rebuild failed; check the build log. `pip install -r server/requirements.txt` should be in the build command. |
| Twilio: "We could not deliver your message" | Webhook URL wrong, or sandbox session expired (re-send the join code from your phone). |
| Reply has Mojibake / garbage Assamese | Twilio is fine with UTF-8; check your phone keyboard is sending Assamese script, not pre-converted bytes. |
