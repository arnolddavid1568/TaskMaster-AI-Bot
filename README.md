# TaskMaster AI Bot

A Telegram bot with PDF, image, document, text, translation, URL,
security, calculator, date, archive, ASCII, developer, and admin
tools — built with `python-telegram-bot` (async, v21).

## Features

- 📄 PDF: merge, split, compress, extract text
- 🖼️ Image: resize, compress, convert, OCR
- 📝 Document: TXT / DOCX / PDF conversion
- 🔤 Text: summarize, rewrite, word count, clean text
- 🌍 Translation between many languages
- 🔗 URL metadata extraction + QR code generation
- 📊 File analysis (type, size, basic contents)
- 🔐 Password generator + hash generator
- 🧮 Calculator (expressions, percentages, unit conversion)
- 📅 Age / date-difference / countdown calculators
- 🗜️ ZIP create / extract
- 🎨 ASCII banner generator
- 💻 Developer tools: JSON formatter, Base64, UUID generator
- 📱 Telegram utilities: ID lookup, formatting cheat sheet
- 📈 Admin dashboard: users, command stats, logs, ban/unban, broadcast
- ⚙️ Background task queue (keeps the bot responsive on big files)
- 🛡️ Per-user rate limiting
- 💾 Auto-expiring temp file storage

## 1. Get a bot token

1. Open Telegram, message **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot` and follow the prompts.
3. Copy the token it gives you (looks like `123456:ABC-DEF...`).

## 2. Find your Telegram user ID (for admin access)

Message **[@userinfobot](https://t.me/userinfobot)** on Telegram, or run
the bot first and send it `/id`.

## 3. Local setup

```bash
git clone <this repo>
cd taskmaster_bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set BOT_TOKEN and ADMIN_IDS
```

Load the `.env` file (either `pip install python-dotenv` and add
`from dotenv import load_dotenv; load_dotenv()` to the top of
`main.py`, or just export the vars manually):

```bash
export $(cat .env | xargs)   # macOS/Linux
python main.py
```

### Optional: OCR support

`/ocr` needs the `tesseract` binary installed on the machine (not just
the `pytesseract` Python package):

- **Railway**: already handled — `nixpacks.toml` in this repo tells
  Railway's builder to install `tesseract` automatically. No action
  needed on your part.
- **Render**: add a `render-build.sh` that runs
  `apt-get install -y tesseract-ocr` before `pip install`, or switch
  the service to a Docker-based deploy with `tesseract-ocr` in the
  base image.
- Ubuntu/Debian (VPS): `sudo apt install tesseract-ocr`
- macOS (local dev): `brew install tesseract`
- If it's missing, `/ocr` will reply with a friendly message instead of
  crashing — everything else still works.

### Optional: better /summarize and /rewrite

By default these use a local, dependency-free algorithm (extractive
summarization / basic cleanup). If you set `ANTHROPIC_API_KEY` in your
environment, the bot automatically upgrades to using Claude for real
AI summarization and rewriting — no code changes needed.

## 4. Deploy to Render (free tier)

1. Push this project to a GitHub repo.
2. In Render, choose **New + → Blueprint**, point it at your repo — it
   will pick up `render.yaml` automatically. (Alternatively: **New +
   → Background Worker**, build command `pip install -r
   requirements.txt`, start command `python main.py`.)
3. Set the `BOT_TOKEN` and `ADMIN_IDS` environment variables in the
   Render dashboard (marked `sync: false` so they're not committed).
4. Deploy. Render's free tier is enough for light-to-moderate usage;
   note free workers can spin down when idle on some plans — check
   Render's current free-tier policy.

## 5. Deploy to Railway (free tier)

1. Push this project to GitHub.
2. In Railway, **New Project → Deploy from GitHub repo**.
3. Railway will detect `Procfile` (worker process). Set `BOT_TOKEN`
   and `ADMIN_IDS` in the **Variables** tab.
4. Deploy.

> This bot uses long-polling (`run_polling`), not webhooks, so it works
> the same way on a VPS, Render, Railway, or your own machine — no
> public HTTPS endpoint required.

## Project structure

```
taskmaster_bot/
├── main.py                 # entrypoint, registers all handlers
├── config.py                # env-var driven configuration
├── database.py               # SQLite: users, command logs, stats
├── handlers/
│   ├── menu.py               # /start, /help, inline button menu
│   ├── state.py               # per-user flow state machine
│   ├── router.py               # routes file uploads to the right tool
│   ├── instant_tools.py        # no-file commands (calc, hash, etc.)
│   └── admin.py                 # /stats /logs /ban /unban /broadcast
├── utils/
│   ├── rate_limiter.py         # sliding-window per-user rate limit
│   ├── task_queue.py            # bounded async task queue
│   ├── file_manager.py           # temp file paths + auto-cleanup
│   ├── decorators.py              # @guarded (ban+rate-limit+logging)
│   └── tools/                      # pure business logic, one file per category
│       ├── pdf_tools.py
│       ├── image_tools.py
│       ├── document_tools.py
│       ├── text_tools.py
│       ├── translation.py
│       ├── url_tools.py
│       ├── file_analysis.py
│       ├── security_tools.py
│       ├── calculator.py
│       ├── date_tools.py
│       ├── archive_tools.py
│       ├── ascii_tools.py
│       └── dev_tools.py
├── requirements.txt
├── nixpacks.toml            # tells Railway to install tesseract (for /ocr)
├── render.yaml
├── Procfile
└── .env.example
```

## How the file-tool flow works

Tools that need an uploaded file (PDF/image/document/archive/analysis)
use a tiny state machine (`handlers/state.py`):

1. User taps a button in `/menu` (or uses a shortcut like `/mergepdf`).
2. The bot sets a "pending action" for that user and asks them to send
   a file.
3. `handlers/router.py` catches the next document/photo, validates its
   type, and either runs the tool immediately, asks for one more text
   parameter (e.g. page range, resize dimensions), or — for
   merge/zip — keeps collecting files until `/done`.
4. The actual work runs through `utils/task_queue.py`, which offloads
   blocking operations to a thread pool with a concurrency cap, so
   large files don't freeze the bot for other users.
5. Downloaded/generated files live under `tmp_files/<user_id>/` and are
   auto-deleted after `FILE_RETENTION_MINUTES` (default 30) by a
   repeating job.

## Adding a new tool

1. Write a pure function in the right `utils/tools/*.py` file (no
   Telegram objects — just paths/strings in, result out).
2. If it's a file tool: add it to `handlers/state.py`
   (`AUTO_RUN_ACTIONS`, `PARAM_ACTIONS`, or `MULTI_FILE_ACTIONS`, plus
   a label), wire it into `EXT_FOR_ACTION_INPUT` and `_execute()` in
   `handlers/router.py`, and optionally add it to a category in
   `handlers/menu.py`.
3. If it's an instant command: add a handler function to
   `handlers/instant_tools.py` and register it with
   `app.add_handler(CommandHandler(...))` in `main.py`.

## Notes & limitations

- `docx_to_pdf` / `txt_to_pdf` render plain text into a PDF layout —
  they preserve content but not rich Word styling (fonts, images,
  tables). For pixel-perfect DOCX→PDF conversion you'd typically shell
  out to LibreOffice (`soffice --headless --convert-to pdf`), which
  isn't included here to keep the free-tier footprint small.
- Translation uses the free `deep-translator` Google backend — no API
  key needed, but it's an unofficial wrapper and could break if Google
  changes its page structure.
- SQLite is used for simplicity; it's fine for a single-instance
  deployment. If you scale to multiple bot instances, move to
  Postgres and swap the rate limiter's in-memory store for Redis.
