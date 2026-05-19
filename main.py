from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from exceptions import MissingRequiredEnvironmentVariable

from colorlog import ColoredFormatter
import logging

import os
import dotenv

import aiogram
import groq

# loading environments from .env in root / of the project
dotenv.load_dotenv()

""" LOGGING """

def setup_logger(level: str = "INFO") -> logging.Logger:
    formatter = ColoredFormatter(
        "%(white)s%(asctime)s%(reset)s "
        "%(log_color)s%(levelname)-7s%(reset)s "
        "%(message_log_color)s%(message)s%(reset)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        },
        secondary_log_colors={
            "message": {
                "DEBUG": "white",
                "INFO": "white",
                "WARNING": "white",
                "ERROR": "red",
                "CRITICAL": "red",
            }
        },
        style="%",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    return logging.getLogger("news_checker_bot")

logger = setup_logger(level="INFO")

""" CONFIG """

config = {
    'BOT_TOKEN': os.getenv('BOT_TOKEN'),
    'GROQ_API_TOKEN': os.getenv('GROQ_API_TOKEN'),
}

missing = [
    name for name, value in config.items() if not value
]
if missing:
    raise MissingRequiredEnvironmentVariable(missing)

bot = aiogram.Bot(token=config['BOT_TOKEN'])
dp = Dispatcher()
groq_client = groq.AsyncGroq(api_key=config['GROQ_API_TOKEN'])

del config # for security

""" COMMANDS """

@dp.message(CommandStart())
async def start(message: Message):
    await message.reply(
        "👋 Hi! I'm a AI based Telegram Bot written on Python!\n"
        "💬🤖 My purpose is - rid the world of fake news or misinformation! ✅\n\n"
        "📰 My model is based on OpenAI/GPT-OSS-120b to ensure accuracy in checking information.\n\n"
        "All you need - just send a <b>fact</b>, <b>citation from an article</b>, or <b>ask me a question</b>!\n\n"
        "🧑‍💻 Project authors: Alim Mun, Amirzhan Kamunov, Maxim Malyshev (3)",
        parse_mode=ParseMode.HTML
    )

""" CONFIGURATION """

LLM_TEMPERATURE = 0.2
LLM_MAX_COMPLETION_TOKENS = 1500
LLM_STREAM = False
LLM_TOOLS = [{"type": "browser_search"}]
LLM_REASONING_EFFORT = "low"
LLM_TOP_P = 1
LLM_MODEL = "openai/gpt-oss-120b"
MAX_TEXT_LENGTH = 1000
LLM_INSTRUCTIONS = """
You are a strict Telegram fact-checking bot.

Check only:
facts, news claims, rumors, article quotes, or serious real-world questions.
Reject math, jokes, spam, personal chat, commands, opinions, and unclear text.

Always use browser_search before answering.
Use only facts found in search results.
Prefer official sources, major media, and fact-checkers.
For current events, use the newest available sources.
If the claim asks about current status, search current status.
If no fresh reliable evidence exists, say so.
Never invent facts, dates, titles, links, or source names.
Never cite a source unless its URL was found by search.
If sources do not clearly support the answer, verdict must be uncertain.

Verdicts:
confirmed = reliable sources support the claim
false = reliable sources contradict the claim
misleading = partly true but distorted
uncertain = evidence is weak, old, missing, or unclear

Confidence:
high = official or multiple strong sources agree
medium = reliable but limited evidence
low = weak, old, mixed, or incomplete evidence

Emoji:
✅ confirmed
❌ false
⚠️ misleading or uncertain

Answer in the same language as the user.
Output only this format:

📰 Headline: <b>max 12 words</b>
📌 Claim type: <b>news / factual claim / question / rumor</b>
EMOJI My verdict: <b>VERDICT</b> with <b>CONFIDENCE confidence</b>

🧾 Summary:
1-2 short sentences. Mention if no fresh info was found.

🧠 Reasons:
• reason under 100 chars
• reason under 100 chars
• reason under 100 chars

🔗 Sources:
• <a href="URL">title under 50 chars</a>
• <a href="URL">title under 50 chars</a>

Rules:
- 1 to 3 reasons.
- 1 to 5 sources.
- Sources must be real URLs from search.
- Do not use Markdown.
- Do not mention browser_search.
- Do not add text outside the format.

If invalid, answer exactly:
❌ It is not a fact, citation from article or a question. Try again, but be careful.
"""

""" MESSAGE HANDLING """

@dp.message()
async def handle_request(message: Message):
    text = (message.text or "").strip()

    if not text:
        await message.reply("❌ Please, send only TEXT messages. Other attachments will be ignored.")
        return
    elif len(text) > MAX_TEXT_LENGTH:
        await message.reply(f"❌ The length of your message cannot be more than {MAX_TEXT_LENGTH} characters.")
        return

    reply = await message.reply(f"⏳ OK. I'm checking the information... Give me a moment, please.")

    try:
        llm_response = await groq_client.chat.completions.create( # type: ignore
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": LLM_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            temperature=LLM_TEMPERATURE,
            max_completion_tokens=LLM_MAX_COMPLETION_TOKENS,
            top_p=LLM_TOP_P,
            reasoning_effort=LLM_REASONING_EFFORT,
            stop=None,
            stream=False,
            tools=LLM_TOOLS
        )

        choice = llm_response.choices[0].message
        content = (choice.content or "").strip()

        if not content:
            await reply.edit_text(
                "❌ An error occurred on Groq model side. Please try again.",
            )
            return
    except groq.RateLimitError:
        logger.warning("Groq API rate limit exceeded.")
        await reply.edit_text(
            "❌ You've hit a rate limit. Try again later.",
        )
        return
    except Exception as e:
        logger.exception(e)
        await reply.edit_text(
            "❌ An unexpected error occurred on the bot side. Please try again.",
        )
        return

    await reply.edit_text(
        text=content,
        disable_web_page_preview=True,
        parse_mode="HTML"
    )

""" BOT UTILS """

async def run():
    await dp.start_polling(bot)

async def shutdown() -> None:
    await bot.session.close()
    logger.info("Bot shutdown complete")
