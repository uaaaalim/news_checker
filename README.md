# News Checker — Telegram Bot

News Checker is an asynchronous Telegram bot that checks news claims, factual statements, rumors, questions, or article quotes with an AI model through the Groq API. The bot is built with `aiogram`, uses long polling, and replies with a short fact-check verdict, reasoning, and HTML links to sources.

## Features

- `/start` command with a short project introduction.
- Text-only fact-checking flow for user messages.
- Input validation for empty messages and messages longer than 1000 characters.
- Groq Chat Completions integration with `openai/gpt-oss-120b`.
- HTML-formatted Telegram responses with disabled link previews.
- Colored console logging and startup metadata output.
- Environment-variable based configuration through `.env`.

## Tech stack

- Python `>=3.13,<3.15`
- aiogram `3.x`
- Groq Python SDK
- python-dotenv
- colorlog
- Poetry

## Project structure

```text
.
├── app.py            # Minimal entrypoint that runs run.main()
├── run.py            # Startup logging, metadata, and graceful shutdown wrapper
├── main.py           # Bot configuration, handlers, LLM prompt, and polling logic
├── exceptions.py     # Custom missing-environment exception
├── pyproject.toml    # Project metadata and Poetry dependencies
├── poetry.lock       # Locked dependency versions
├── alembic.ini       # Legacy config file; the current app does not use a database
└── README.md
```

## Requirements

Install these tools before running the bot:

- Python 3.13 or newer within the supported range.
- Poetry.
- A Telegram bot token from [BotFather](https://t.me/BotFather).
- A Groq API token.

> The current code does not use PostgreSQL, SQLAlchemy, or Alembic migrations. Only `BOT_TOKEN` and `GROQ_API_TOKEN` are required at runtime.

## Quick start

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd news_checker
```

### 2. Keep Poetry's virtual environment inside the project

```bash
poetry config virtualenvs.in-project true
```

Optional check:

```bash
poetry config virtualenvs.in-project
```

The command should print `true`, and Poetry will create the environment in `./.venv`.

### 3. Install dependencies

```bash
poetry env use 3.13
poetry install
```

### 4. Create `.env`

Create a `.env` file in the repository root:

```env
BOT_TOKEN=1234567890:your_telegram_bot_token
GROQ_API_TOKEN=gsk_your_groq_api_token
```

Required variables:

| Variable | Description |
| --- | --- |
| `BOT_TOKEN` | Telegram bot token issued by BotFather. |
| `GROQ_API_TOKEN` | Groq API token used by the AI fact-checking model. |

### 5. Run the bot

```bash
poetry run python app.py
```

You can also run the wrapper directly:

```bash
poetry run python run.py
```

When the bot starts, it logs project metadata, Python version, aiogram version, Groq SDK version, and then starts polling Telegram.

## How it works

1. `app.py` starts the async entrypoint from `run.py`.
2. `run.py` prints startup metadata and calls `main.run()`.
3. `main.py` loads `.env`, validates required variables, creates the Telegram bot, dispatcher, and Groq async client.
4. A `/start` handler explains how to use the bot.
5. Any regular text message is sent to the configured Groq model with strict fact-checking instructions.
6. The bot edits the temporary “checking” message with the final verdict.
7. On shutdown, the Telegram bot session is closed cleanly.

## User input rules

The bot accepts:

- news claims;
- factual claims;
- real-world rumors;
- serious real-world questions;
- quotes from news or articles.

The bot rejects unsupported or unclear input such as empty messages, attachments, spam, jokes, math tasks, personal chat, and messages over 1000 characters.

## AI response format

The prompt in `main.py` asks the model to return:

- a short headline;
- claim type;
- verdict: `confirmed`, `false`, `misleading`, or `uncertain`;
- confidence level: `high`, `medium`, or `low`;
- a 1–2 sentence summary;
- 1–3 short reasons;
- 1–5 HTML source links.

Telegram responses use `parse_mode="HTML"`, so source links should be valid HTML anchors.

## Configuration notes

Most LLM settings are currently constants in `main.py`:

| Constant | Current value |
| --- | --- |
| `LLM_MODEL` | `openai/gpt-oss-120b` |
| `LLM_TEMPERATURE` | `0.2` |
| `LLM_MAX_COMPLETION_TOKENS` | `1500` |
| `LLM_REASONING_EFFORT` | `low` |
| `MAX_TEXT_LENGTH` | `1000` |

If you need to change the model, token limit, temperature, or maximum user message length, update these constants in `main.py`.

## Useful commands

Install dependencies:

```bash
poetry install
```

Run the bot:

```bash
poetry run python app.py
```

Run Python syntax checks:

```bash
python -m compileall app.py run.py main.py exceptions.py
```

Show project metadata from Poetry:

```bash
poetry check
```

## Deployment with systemd on Ubuntu

Create a service file, for example `/etc/systemd/system/news-checker.service`:

```ini
[Unit]
Description=News Checker Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/news_checker
Environment=PATH=/opt/news_checker/.venv/bin:/usr/bin:/bin
ExecStart=/opt/news_checker/.venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable news-checker
sudo systemctl start news-checker
sudo systemctl status news-checker
```

View logs:

```bash
journalctl -u news-checker -f
```

## Troubleshooting

### `Environment variables 'BOT_TOKEN, GROQ_API_TOKEN' is required`

Create `.env` in the project root and make sure it contains both required variables.

### Telegram bot does not answer

Check that:

- the bot token is valid;
- the bot is running without exceptions;
- no other process is polling the same Telegram bot token.

### Groq errors or rate limits

Check that:

- `GROQ_API_TOKEN` is valid;
- the selected model is available for your Groq account;
- your account has enough quota;
- you are not exceeding API rate limits.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

Alim Mun — 2026, with love from Kazakhstan.
