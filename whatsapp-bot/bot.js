/**
 * Brajawali WhatsApp bot.
 *
 * Runs as a WhatsApp Web client on your machine. On first run, scan the
 * QR code with WhatsApp on your phone (Settings → Linked Devices → Link
 * a Device). The session is persisted in `.wwebjs_auth/` so subsequent
 * starts are seamless.
 *
 * Usage in any WhatsApp chat (group or DM):
 *
 *     /braja মই তোমাক ভাল পাওঁ
 *
 * The bot only responds to messages YOU sent (so people you chat with
 * don't accidentally trigger it), unless ALLOW_OTHERS=1 is set, in which
 * case anyone messaging you can use /braja too.
 *
 * To make the bot reply in your own chats: just send /braja <text> in
 * any chat. The bot sees your message and replies into the same chat.
 *
 * Logout / re-pair: `npm run logout` then `npm start`.
 */

import pkg from "whatsapp-web.js";
const { Client, LocalAuth } = pkg;
import qrcode from "qrcode-terminal";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(__dirname, "..");
const TRANSLATE_BIN = path.join(SKILL_ROOT, "translate"); // wrapper script

const COMMAND = "/braja";
const HELP_COMMAND = "/braja-help";
const ALLOW_OTHERS = process.env.ALLOW_OTHERS === "1";

// ---- translator subprocess ------------------------------------------------

/**
 * Run ./translate "<text>" and parse the JSON output.
 * Times out after 15s. Returns null on failure.
 */
function translate(text) {
  return new Promise((resolve) => {
    const child = spawn(TRANSLATE_BIN, [text], { cwd: SKILL_ROOT });
    let out = "", err = "";
    const timer = setTimeout(() => {
      try { child.kill("SIGKILL"); } catch {}
      resolve({ error: "timeout" });
    }, 15000);

    child.stdout.on("data", (b) => { out += b.toString("utf8"); });
    child.stderr.on("data", (b) => { err += b.toString("utf8"); });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        return resolve({ error: `exit ${code}: ${err.trim() || "no output"}` });
      }
      try {
        resolve(JSON.parse(out));
      } catch (e) {
        resolve({ error: `parse: ${e.message}; raw: ${out.slice(0, 200)}` });
      }
    });
  });
}

// ---- formatting ----------------------------------------------------------

function formatReply(translation) {
  if (translation.error) {
    return `❌ ${translation.error}`;
  }
  const lines = [];
  lines.push(`*${translation.brajawali}*`);
  lines.push("");
  lines.push(`_input: ${translation.normalised_assamese}_`);
  lines.push("");
  lines.push("Word-by-word:");
  for (const tok of translation.alignment) {
    const tag = ({
      core: "✓",
      dictionary: "✓",
      fuzzy: "≈",
      biprokorso: "~",
      unknown: "?",
    })[tok.source] || (tok.source.includes("morph") ? "*" : "·");
    lines.push(`  ${tag} ${tok.asm} → ${tok.braja}`);
  }
  if (translation.metadata?.unknown_count) {
    lines.push("");
    lines.push(`_${translation.metadata.unknown_count} unknown of ${translation.metadata.token_count}_`);
  }
  return lines.join("\n");
}

const HELP_TEXT = `🪷 *Brajawali Bot*

Translate Assamese (or Roman-Assamese) into Brajawali — Sankaradeva's literary language.

*Usage:*
\`/braja <text>\`

*Examples:*
• /braja মই তোমাক ভাল পাওঁ
• /braja তেওঁ ঘৰলৈ গ'ল
• /braja moi tumar logot ahisilo

Source: Sri Sri Narayan Chandra Goswami,
ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান (1990)`;

// ---- bot client ----------------------------------------------------------

// Detect a usable browser. whatsapp-web.js's bundled puppeteer-core does
// NOT ship a Chromium binary, so we point it at any installed browser.
import { existsSync } from "node:fs";
const BROWSER_CANDIDATES = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium-browser",
  "/usr/bin/chromium",
].filter(Boolean);
const browserPath = BROWSER_CANDIDATES.find((p) => existsSync(p));
if (!browserPath) {
  console.error(
    "✗ No Chrome/Chromium/Edge/Brave found. Install Chrome (https://chrome.google.com)\n" +
    "  or set CHROME_PATH=/path/to/your/browser"
  );
  process.exit(1);
}
console.log("Using browser:", browserPath);

const client = new Client({
  authStrategy: new LocalAuth({ clientId: "brajawali" }),
  puppeteer: {
    headless: true,
    executablePath: browserPath,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

client.on("qr", (qr) => {
  console.log("\n📱 Scan this QR with WhatsApp:");
  console.log("   (WhatsApp → Settings → Linked Devices → Link a Device)\n");
  qrcode.generate(qr, { small: true });
});

client.on("authenticated", () => {
  console.log("✓ Authenticated. Session saved to .wwebjs_auth/");
});

client.on("ready", () => {
  console.log("✅ Bot is ready.");
  console.log(`   Trigger: send "${COMMAND} <text>" in any chat.`);
  console.log(`   Help:    send "${HELP_COMMAND}"`);
  console.log(`   ALLOW_OTHERS=${ALLOW_OTHERS ? "1 (anyone can use)" : "0 (only your own messages)"}`);
});

client.on("auth_failure", (msg) => {
  console.error("✗ Auth failed:", msg);
});

client.on("disconnected", (reason) => {
  console.warn("⚠ Disconnected:", reason);
});

async function handleMessage(msg) {
  const body = (msg.body || "").trim();

  // Only respond to commands
  if (!body.startsWith(COMMAND) && body !== HELP_COMMAND) {
    return;
  }

  // Permission filter: by default, only respond to messages YOU sent.
  // (msg.fromMe means the message originated from this account.)
  if (!ALLOW_OTHERS && !msg.fromMe) {
    return;
  }

  // Help
  if (body === HELP_COMMAND || body === COMMAND || body === `${COMMAND} help`) {
    await msg.reply(HELP_TEXT);
    return;
  }

  // Strip command, get the actual text
  const text = body.slice(COMMAND.length).trim();
  if (!text) {
    await msg.reply(HELP_TEXT);
    return;
  }

  console.log(`[${new Date().toISOString()}] translate: ${text.slice(0, 80)}`);
  const result = await translate(text);
  const reply = formatReply(result);

  try {
    await msg.reply(reply);
  } catch (e) {
    console.error("send failed:", e.message);
  }
}

client.on("message_create", handleMessage);

console.log("Starting Brajawali WhatsApp bot…");
client.initialize().catch((e) => {
  console.error("Failed to initialize:", e);
  process.exit(1);
});
