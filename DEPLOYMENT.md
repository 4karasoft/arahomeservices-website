# Deployment notes

## How to debug: why aren’t inventory items showing up?

When you send a message in the Telegram group, the flow is: **Telegram → POST to your webhook → your app parses and saves**. If nothing appears in the DB, something in that chain is failing.

### 1. Check that the webhook is being called

In DigitalOcean: **Your App → Runtime Logs** (or the log stream for your container). Send a message in the group and watch the logs.

- You should see: **`[Telegram webhook] Received update_id=...`**  
  If you never see this, Telegram is not hitting your app (webhook not set, wrong URL, or network/SSL issue).
- Then one of:
  - **`[Telegram webhook] Saved inventory item ...`** → message was saved.
  - **`[Telegram webhook] Ignored: ...`** → message was skipped (reason is in the log).

### 2. Use the log messages to find the reason

The code logs why it skipped a message. Match what you see to this table:

| Log message | Meaning |
|-------------|--------|
| `Ignored: no message in update` | Update had no `message` (e.g. other update type). |
| `Ignored: message from bot` | Message was sent by a bot. |
| `Ignored: chat_type=... (need group/supergroup)` | Chat is not a group/supergroup (e.g. private chat). |
| `Ignored: TELEGRAM_INVENTORY_GROUP_CHAT_ID not set` | Env var not set in the container. |
| `Ignored: chat_id X != expected Y` | Message is from a different group; set `TELEGRAM_INVENTORY_GROUP_CHAT_ID` to the group that sends the message (and get the real group ID from a bot like @userinfobot). |
| `Ignored: message too short` | Message has fewer than 5 characters. |
| `Ignored: duplicate message_id=...` | Already saved (e.g. same message processed twice). |

### 3. Confirm webhook and group ID

- **Webhook:**  
  `curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"`  
  Check `url` and `last_error_message` (if any).
- **Group ID:**  
  Add @userinfobot to the group, send a message, and use the **group chat id** (negative number) as `TELEGRAM_INVENTORY_GROUP_CHAT_ID` in the app’s environment.

### 4. Redeploy after env changes

If you change `TELEGRAM_INVENTORY_GROUP_CHAT_ID` (or any env var), redeploy the app so the container gets the new value.

---

## Why "no such table" kept coming back

- **Cause:** On container-based deploys (e.g. DigitalOcean App Platform), the **release command** (where you run `migrate`) often runs in a **different container** than the one that serves HTTP. So the database that got migrated is in container A; the web app runs in container B and uses a different (empty) SQLite file. After a deploy or restart, the web container has no tables again.
- **Fix applied:** The Dockerfile CMD now runs `migrate` **then** gunicorn in the **same** container. So the process that serves traffic is the one that ran migrate; the DB file and the app share the same filesystem.

## Will the database update / keep data when the container restarts?

**No.** By default the database is **not** updated in the sense of “keeping your data.” Here’s what happens:

- The SQLite file lives **inside the container** (e.g. `/app/db.sqlite3`).
- When the container **restarts** or is **replaced** (e.g. new deploy), that filesystem is usually **thrown away**. So:
  - Tables are recreated (because the Dockerfile runs `migrate` on startup).
  - **All existing data (inventory items, etc.) is lost**; the DB starts empty again.

So: **every time the container restarts or you deploy, the DB is effectively reset.** To keep data across restarts you need either a **persistent volume** for SQLite or a **managed database** (e.g. PostgreSQL).

## Data loss on restart (SQLite)

- By default the SQLite file lives inside the container. If the platform **does not** persist the container filesystem across restarts/deploys, **all data is lost** on each new deploy or restart (inventory, etc. will be empty again).
- **To keep data across restarts:**
  1. **Persistent volume:** If your platform supports mounting a volume, set `DATABASE_PATH` to a path on that volume (e.g. `/data/db.sqlite3`) so the DB file is stored on the volume and survives restarts.
  2. **Managed database:** For production, use a managed PostgreSQL (or MySQL) and point Django at it via `DATABASE_URL`. Then run `migrate` once (e.g. in release command); all app instances share the same database and data persists.

## DigitalOcean: keep database across rebuilds and restarts

To avoid losing inventory (and other data) on every deploy or container restart, put the SQLite file on a **persistent volume** and point the app at it.

### Steps (App Platform)

1. **Create a volume**  
   In the DigitalOcean dashboard: **Apps → your app → Settings → App-Level Resources → Volumes → Create Volume**. Give it a name (e.g. `db-volume`) and a size (e.g. 1 GB).

2. **Mount the volume**  
   In the same app, open the **Component** that runs your container (e.g. the web service). Under **Volume Mounts**, add a mount:  
   - **Volume:** the volume you created  
   - **Mount Path:** `/data` (or another path you prefer)

3. **Set the database path**  
   In **App-Level** or **Component-Level** environment variables, add:  
   - **Name:** `DATABASE_PATH`  
   - **Value:** `/data/db.sqlite3` (must match the mount path + filename)

4. **Redeploy** the app. On first run, the app will create `/data/db.sqlite3` on the volume; that file will persist across restarts and rebuilds.

If `DATABASE_PATH` is not set, the app keeps using the default path inside the container (`BASE_DIR / 'db.sqlite3'`), and data is lost on each new container.
