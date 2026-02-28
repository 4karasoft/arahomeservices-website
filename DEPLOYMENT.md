# Deployment notes

## Why "no such table" kept coming back

- **Cause:** On container-based deploys (e.g. DigitalOcean App Platform), the **release command** (where you run `migrate`) often runs in a **different container** than the one that serves HTTP. So the database that got migrated is in container A; the web app runs in container B and uses a different (empty) SQLite file. After a deploy or restart, the web container has no tables again.
- **Fix applied:** The Dockerfile CMD now runs `migrate` **then** gunicorn in the **same** container. So the process that serves traffic is the one that ran migrate; the DB file and the app share the same filesystem.

## Data loss on restart (SQLite)

- By default the SQLite file lives inside the container. If the platform **does not** persist the container filesystem across restarts/deploys, **all data is lost** on each new deploy or restart (inventory, etc. will be empty again).
- **To keep data across restarts:**
  1. **Persistent volume:** If your platform supports mounting a volume, set `DATABASE_PATH` to a path on that volume (e.g. `/data/db.sqlite3`) so the DB file is stored on the volume and survives restarts.
  2. **Managed database:** For production, use a managed PostgreSQL (or MySQL) and point Django at it via `DATABASE_URL`. Then run `migrate` once (e.g. in release command); all app instances share the same database and data persists.

## Optional: put SQLite on a persistent volume

Set in your app environment:

```bash
DATABASE_PATH=/data/db.sqlite3
```

Then mount a volume at `/data` (or whatever path you use) so that directory persists across deploys/restarts.
