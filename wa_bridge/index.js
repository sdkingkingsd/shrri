// wa_bridge/index.js
// Baileys-based WhatsApp sidecar. Exposes HTTP endpoints so the Python
// engine (dispatcher.py / whatsapp_tool.py) can send/reply/delete/forward
// without driving a browser.

const makeWASocket = require('@whiskeysockets/baileys').default;
const {
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  DisconnectReason,
} = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const express = require('express');
const P = require('pino');

const PORT = process.env.WA_BRIDGE_PORT || 3001;
const AUTH_DIR = __dirname + '/auth';

const app = express();
app.use(express.json());

let sock = null;
let isConnected = false;

// We maintain our own minimal contact map instead of using Baileys'
// built-in makeInMemoryStore. The built-in store has a known bug where
// certain contacts.update events throw ("Cannot convert undefined or
// null to object" — WhiskeySockets/Baileys#747), and we only need
// name -> jid lookups, not the full chat/message store it provides.
const contactNames = new Map(); // jid -> best-known display name

const fs = require('fs');
const CONTACTS_FILE = __dirname + '/contacts.json';

function loadContactNames() {
  try {
    if (fs.existsSync(CONTACTS_FILE + '.enc')) {
      try {
        const { execSync } = require('child_process');
        execSync(`python3 ${__dirname}/crypt_bridge.py decrypt-json ${CONTACTS_FILE}`);
      } catch(e) { console.warn('[wa_bridge] Warning: could not decrypt contacts.json:', e.message); }
    }
    if (fs.existsSync(CONTACTS_FILE)) {
      const raw = JSON.parse(fs.readFileSync(CONTACTS_FILE, 'utf8'));
      for (const [jid, name] of Object.entries(raw)) contactNames.set(jid, name);
      console.log(`[wa_bridge] Loaded ${contactNames.size} cached contact names.`);
    }
  } catch (e) {
    console.log('[wa_bridge] Could not load cached contacts:', e.message);
  }
}

let saveTimer = null;
function flushContactNames() {
  try {
    fs.writeFileSync(CONTACTS_FILE, JSON.stringify(Object.fromEntries(contactNames)));
    // Re-encrypt immediately after writing plain file.
    try {
      const { execSync } = require('child_process');
      execSync(`python3 ${__dirname}/crypt_bridge.py encrypt-json ${CONTACTS_FILE}`);
    } catch(e) { console.warn('[wa_bridge] Warning: could not encrypt contacts.json:', e.message); }
  } catch (e) {
    console.log('[wa_bridge] Could not save contacts:', e.message);
  }
}

function saveContactNamesDebounced() {
  if (saveTimer) return;
  saveTimer = setTimeout(() => {
    saveTimer = null;
    flushContactNames();
  }, 2000);
}

function updateContactName(jid, contact) {
  if (!jid || !contact) return;
  const name = contact.name || contact.notify || contact.verifiedName;
  if (name) {
    contactNames.set(jid, name);
    saveContactNamesDebounced();
  }
}

// In-memory cache of recent messages per chat, newest last.
// Used by /reply (quote the latest message) and /forward (grab the latest
// message's content). Keeps the last 50 messages per chat — enough for
// "last message" lookups without unbounded memory growth.
//
// Also persisted to disk (trimmed to just the fields Baileys' `quoted`
// option actually needs: key, message, messageTimestamp, pushName) so a
// bridge restart doesn't go back to a cold, empty history for every chat.
const recentMessages = new Map(); // jid -> array of message objects
const MESSAGES_FILE = __dirname + '/recent_messages.json';
const PERSIST_PER_CHAT = 20; // smaller than the 50 in-memory cap -- plenty for "last message" lookups

function loadRecentMessages() {
  try {
    if (fs.existsSync(MESSAGES_FILE + '.enc')) {
      try {
        const { execSync } = require('child_process');
        execSync(`python3 ${__dirname}/crypt_bridge.py decrypt-json ${MESSAGES_FILE}`);
      } catch(e) { console.warn('[wa_bridge] Warning: could not decrypt recent_messages.json:', e.message); }
    }
    if (fs.existsSync(MESSAGES_FILE)) {
      const raw = JSON.parse(fs.readFileSync(MESSAGES_FILE, 'utf8'));
      for (const [jid, arr] of Object.entries(raw)) recentMessages.set(jid, arr);
      console.log(`[wa_bridge] Loaded message history for ${recentMessages.size} chats.`);
    }
  } catch (e) {
    console.log('[wa_bridge] Could not load cached message history:', e.message);
  }
}

let msgSaveTimer = null;
// Strips large inline binary fields (thumbnails, etc.) that media messages
// carry inside `message.*Message.jpegThumbnail`. We keep enough structure
// for Baileys' `quoted` option to work (key, message shape, timestamp),
// but don't need the actual thumbnail bytes on disk — /reply and /forward
// only use the text content today, and quoting a media message without
// its thumbnail still works fine (WhatsApp just re-fetches it from the
// original media's directPath).
function stripBinaryFields(message) {
  if (!message || typeof message !== 'object') return message;
  const clone = JSON.parse(JSON.stringify(message));
  for (const key of Object.keys(clone)) {
    const sub = clone[key];
    if (sub && typeof sub === 'object') {
      delete sub.jpegThumbnail;
      delete sub.thumbnailSha256;
    }
  }
  return clone;
}

// The actual, synchronous write. Called both from the debounced timer
// (normal operation — batches rapid-fire saves) and directly from the
// shutdown handler (so Ctrl+C / process exit doesn't lose whatever
// arrived in the last <2s debounce window, which is exactly what
// happened during testing before this fix existed).
function flushRecentMessages() {
  try {
    const trimmed = {};
    for (const [jid, arr] of recentMessages.entries()) {
      trimmed[jid] = arr.slice(-PERSIST_PER_CHAT).map((m) => ({
        key: m.key,
        message: stripBinaryFields(m.message),
        messageTimestamp: m.messageTimestamp,
        pushName: m.pushName,
      }));
    }
    fs.writeFileSync(MESSAGES_FILE, JSON.stringify(trimmed));
    // Re-encrypt immediately after writing plain file.
    try {
      const { execSync } = require('child_process');
      execSync(`python3 ${__dirname}/crypt_bridge.py encrypt-json ${MESSAGES_FILE}`);
    } catch(e) { console.warn('[wa_bridge] Warning: could not encrypt recent_messages.json:', e.message); }
  } catch (e) {
    console.log('[wa_bridge] Could not save message history:', e.message);
  }
}

function saveRecentMessagesDebounced() {
  if (msgSaveTimer) return;
  msgSaveTimer = setTimeout(() => {
    msgSaveTimer = null;
    flushRecentMessages();
  }, 2000);
}

function rememberMessage(jid, msg) {
  if (!recentMessages.has(jid)) recentMessages.set(jid, []);
  const arr = recentMessages.get(jid);
  const id = msg && msg.key ? msg.key.id : null;
  if (id && arr.length > 0 && arr[arr.length - 1].key && arr[arr.length - 1].key.id === id) {
    return;
  }
  arr.push(msg);
  if (arr.length > 50) arr.shift();
  saveRecentMessagesDebounced();
}

function isRealContentMessage(m) {
  // protocolMessage covers revokes (deletes), edits-as-protocol, and other
  // non-content signals — these aren't "messages" a human would reply to
  // or forward, so we skip them when looking for "the latest message".
  if (!m.message) return false;
  if (m.message.protocolMessage) return false;
  return true;
}

function getLastMessage(jid, { onlyMine = false } = {}) {
  const arr = recentMessages.get(jid) || [];
  for (let i = arr.length - 1; i >= 0; i--) {
    if (!isRealContentMessage(arr[i])) continue;
    if (!onlyMine || arr[i].key.fromMe) return arr[i];
  }
  return null;
}

// --- Contact resolution -----------------------------------------------
// Matches by display name (case-insensitive substring) against our own
// contactNames map, populated from contacts.upsert/contacts.update events.
// Picks the shortest matching name to avoid e.g. "Nag" matching a long
// group-description string before the real contact "Naghul Vit".
function findJidByName(name) {
  const needle = name.toLowerCase();
  let best = null;
  for (const [jid, displayName] of contactNames.entries()) {
    const lower = (displayName || '').toLowerCase();
    if (lower && lower.includes(needle)) {
      if (!best || lower.length < best.nameLen) {
        best = { jid, nameLen: lower.length, displayName };
      }
    }
  }
  return best;
}

async function resolveJid(contactOrJid) {
  if (contactOrJid.endsWith('@s.whatsapp.net') || contactOrJid.endsWith('@g.us') || contactOrJid.endsWith('@lid')) {
    const name = contactNames.get(contactOrJid) || contactOrJid;
    return { jid: contactOrJid, displayName: name };
  }
  // bare phone number?
  if (/^\+?\d{7,15}$/.test(contactOrJid)) {
    const digits = contactOrJid.replace(/^\+/, '');
    return { jid: `${digits}@s.whatsapp.net`, displayName: contactOrJid };
  }
  const match = findJidByName(contactOrJid);
  if (match) return { jid: match.jid, displayName: match.displayName };
  return null;
}

// --- Connection lifecycle -----------------------------------------------
async function startSock() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger: P({ level: 'warn' }),
    printQRInTerminal: false, // we handle QR ourselves below for clearer logging
    syncFullHistory: false,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n=== Scan this QR code with WhatsApp (Linked Devices > Link a Device) ===\n');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'open') {
      isConnected = true;
      console.log('[wa_bridge] Connected to WhatsApp.');
    }

    if (connection === 'close') {
      isConnected = false;
      const statusCode = (lastDisconnect?.error instanceof Boom)
        ? lastDisconnect.error.output?.statusCode
        : null;
      const loggedOut = statusCode === DisconnectReason.loggedOut;
      console.log(`[wa_bridge] Connection closed (code=${statusCode}). Logged out: ${loggedOut}`);
      if (!loggedOut) {
        console.log('[wa_bridge] Reconnecting...');
        startSock();
      } else {
        console.log('[wa_bridge] Logged out — delete the auth/ folder and restart to re-pair.');
      }
    }
  });

  sock.ev.on('contacts.upsert', (contacts) => {
    for (const c of contacts) updateContactName(c.id, c);
  });

  sock.ev.on('contacts.update', (updates) => {
    for (const u of updates) updateContactName(u.id, u);
  });

  sock.ev.on('messages.upsert', ({ messages }) => {
    for (const m of messages) {
      if (!m.message) continue;
      const jid = m.key.remoteJid;
      if (!jid) continue;
      rememberMessage(jid, m);
      // pushName is the sender's self-set WhatsApp display name — a
      // reliable fallback for contacts that never trigger a full
      // contacts.upsert sync (e.g. people not in your phone's address
      // book who you've still chatted with).
      if (!m.key.fromMe && m.pushName && !jid.endsWith('@g.us')) {
        if (!contactNames.has(jid)) {
          contactNames.set(jid, m.pushName);
          saveContactNamesDebounced();
        }
      }
      // Fire auto-reply webhook for incoming 1-on-1 messages.
      if (!m.key.fromMe) console.log("[wa_bridge] Incoming message from", jid, ":", extractText(m.message));
      if (!m.key.fromMe && !jid.endsWith('@g.us') && !jid.endsWith('@newsletter') && m.message) {
        const text = extractText(m.message);
        if (text) {
          const senderName = contactNames.get(jid) || m.pushName || jid;
          try {
            const http = require('http');
            const body = JSON.stringify({ jid, name: senderName, text });
            const req = http.request({
              hostname: '127.0.0.1', port: 3002, path: '/incoming',
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
            });
            req.on('error', () => {}); // silently ignore if auto-reply server is down
            req.write(body);
            req.end();
          } catch(e) {}
        }
      }
    }
  });
}

function requireConnected(res) {
  if (!isConnected || !sock) {
    res.status(503).json({ ok: false, error: 'GAP: WhatsApp bridge not connected yet.' });
    return false;
  }
  return true;
}

function extractText(message) {
  if (!message) return '';
  return (
    message.conversation ||
    message.extendedTextMessage?.text ||
    message.imageMessage?.caption ||
    message.videoMessage?.caption ||
    ''
  );
}

// --- HTTP endpoints -----------------------------------------------------

app.get('/health', (req, res) => {
  res.json({ ok: true, connected: isConnected, known_contacts: contactNames.size });
});

// Debug helper — lists what the bridge currently knows, so you can check
// whether a contact name will resolve before trying send/reply/delete.
app.get('/contacts', (req, res) => {
  const list = Array.from(contactNames.entries()).map(([jid, name]) => ({ jid, name }));
  res.json({ ok: true, count: list.length, contacts: list });
});

// Manually add a name -> phone mapping, instead of waiting for WhatsApp's
// own (slow, unpredictable) contact sync to push it. Useful for seeding
// contacts you know you'll want to message by name right away.
// POST { name: "Shrri Varshan", phone: "919xxxxxxxxx" }
app.post('/contacts/add', (req, res) => {
  try {
    const { name, phone } = req.body;
    if (!name || !phone) {
      return res.status(400).json({ ok: false, error: 'GAP: name and phone are required' });
    }
    const digits = phone.replace(/^\+/, '').replace(/\s/g, '');
    if (!/^\d{7,15}$/.test(digits)) {
      return res.status(400).json({ ok: false, error: 'GAP: phone must be digits only, with country code (e.g. 919876543210)' });
    }
    const jid = `${digits}@s.whatsapp.net`;
    contactNames.set(jid, name);
    saveContactNamesDebounced();
    res.json({ ok: true, result: `Added contact: ${name} -> ${jid}` });
  } catch (e) {
    res.json({ ok: false, error: `GAP: failed to add contact — ${e.message}` });
  }
});

// POST { contact: "Naghul Vit" or "+9198xxxxxxx" or full jid, text: "..." }
app.post('/send', async (req, res) => {
  if (!requireConnected(res)) return;
  try {
    const { contact, text } = req.body;
    if (!contact || !text) {
      return res.status(400).json({ ok: false, error: 'GAP: contact and text are required' });
    }
    const resolved = await resolveJid(contact);
    if (!resolved) {
      return res.json({ ok: false, error: `GAP: no contact found matching '${contact}'` });
    }
    const sent = await sock.sendMessage(resolved.jid, { text });
    rememberMessage(resolved.jid, sent);
    res.json({ ok: true, result: `Message sent to ${resolved.displayName}: "${text}"` });
  } catch (e) {
    res.json({ ok: false, error: `GAP: send failed — ${e.message}` });
  }
});

// POST { contact: "...", text: "..." } — quote-replies to the latest message in that chat
app.post('/reply', async (req, res) => {
  if (!requireConnected(res)) return;
  try {
    const { contact, text } = req.body;
    if (!contact || !text) {
      return res.status(400).json({ ok: false, error: 'GAP: contact and text are required' });
    }
    const resolved = await resolveJid(contact);
    if (!resolved) {
      return res.json({ ok: false, error: `GAP: no contact found matching '${contact}'` });
    }
    const last = getLastMessage(resolved.jid);
    if (!last) {
      return res.json({ ok: false, error: 'GAP: no messages found to reply to. Try sending a message in that chat first so the bridge can see history.' });
    }
    const sent = await sock.sendMessage(resolved.jid, { text }, { quoted: last });
    rememberMessage(resolved.jid, sent);
    res.json({ ok: true, result: `Replied to ${resolved.displayName}: "${text}"` });
  } catch (e) {
    res.json({ ok: false, error: `GAP: reply failed — ${e.message}` });
  }
});

// POST { contact: "..." } — deletes the last message *you* sent in that chat
app.post('/delete', async (req, res) => {
  if (!requireConnected(res)) return;
  try {
    const { contact } = req.body;
    if (!contact) {
      return res.status(400).json({ ok: false, error: 'GAP: contact is required' });
    }
    const resolved = await resolveJid(contact);
    if (!resolved) {
      return res.json({ ok: false, error: `GAP: no contact found matching '${contact}'` });
    }
    const lastMine = getLastMessage(resolved.jid, { onlyMine: true });
    if (!lastMine) {
      return res.json({ ok: false, error: 'GAP: no sent messages found in bridge history for this chat. The bridge only knows about messages sent/seen since it started — try sending a fresh message first.' });
    }
    await sock.sendMessage(resolved.jid, { delete: lastMine.key });
    res.json({ ok: true, result: `Last message to ${resolved.displayName} deleted.` });
  } catch (e) {
    res.json({ ok: false, error: `GAP: delete failed — ${e.message}` });
  }
});

// POST { from_contact: "...", to_contact: "..." } — forwards the latest message
app.post('/forward', async (req, res) => {
  if (!requireConnected(res)) return;
  try {
    const { from_contact, to_contact } = req.body;
    if (!from_contact || !to_contact) {
      return res.status(400).json({ ok: false, error: 'GAP: from_contact and to_contact are required' });
    }
    const fromResolved = await resolveJid(from_contact);
    const toResolved = await resolveJid(to_contact);
    if (!fromResolved) {
      return res.json({ ok: false, error: `GAP: no contact found matching '${from_contact}'` });
    }
    if (!toResolved) {
      return res.json({ ok: false, error: `GAP: no contact found matching '${to_contact}'` });
    }
    const last = getLastMessage(fromResolved.jid);
    if (!last) {
      return res.json({ ok: false, error: 'GAP: no messages found to forward.' });
    }
    const text = extractText(last.message);
    if (!text) {
      return res.json({ ok: false, error: 'GAP: latest message is non-text (media/other) — forwarding non-text messages is not supported yet.' });
    }
    const sent = await sock.sendMessage(toResolved.jid, {
      text,
      contextInfo: { isForwarded: true, forwardingScore: 1 },
    });
    rememberMessage(toResolved.jid, sent);
    res.json({ ok: true, result: `Forwarded message from ${fromResolved.displayName} to ${toResolved.displayName}` });
  } catch (e) {
    res.json({ ok: false, error: `GAP: forward failed — ${e.message}` });
  }
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`[wa_bridge] HTTP server listening on http://127.0.0.1:${PORT}`);
});

// Flush both caches to disk before the process actually exits — without
// this, Ctrl+C (SIGINT) or `systemctl stop` (SIGTERM) can land inside the
// 2-second debounce window and silently lose whatever changed since the
// last save. This is what caused the test history loss during dev.
function shutdown(signal) {
  console.log(`[wa_bridge] Received ${signal}, flushing state and exiting...`);
  flushContactNames();
  flushRecentMessages();
  setTimeout(() => process.exit(0), 1500);
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

loadContactNames();
loadRecentMessages();
startSock();
