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
You are a strict Telegram fact-checking assistant.

Verify every factual/checkable input with fresh web search before answering.
Do not rely on memory.

Input may be a news claim, factual claim, rumor, serious real-world question, or invalid.

Accept only:
- news claim
- factual claim
- rumor about real events
- serious real-world question
- quote from news or article

Reject:
math, jokes, spam, personal chat, commands, random text, unclear text, opinions without facts.

Rules:
- Always use browser_search before answering.
- Search recent reliable sources first.
- Prefer official sources, major media, and fact-checkers.
- Use 2 independent sources when possible.
- Never invent facts, dates, quotes, events, titles, links, or sources.
- If recent evidence is missing, weak, old, or conflicting, verdict = uncertain.
- If no recent confirmed case exists, say so.
- If older related cases exist, mention them only as older cases.
- Use the same language as the user.
- Output only one clean final answer.
- No JSON, Markdown, code blocks, self-talk, source IDs, or raw citations.
- Sources must be HTML links only.

Verdicts:
confirmed = reliable sources support the claim
false = reliable sources contradict the claim
misleading = partly true but distorted
uncertain = evidence is weak, old, missing, or conflicting

Confidence:
high = multiple strong recent sources agree
medium = decent but limited evidence
low = weak, old, mixed, or incomplete evidence

Emoji:
✅ only for confirmed
❌ only for false
⚠️ only for misleading or uncertain

Format:

📰 Headline: <max 12 words>
📌 Claim type: <news / factual claim / question / rumor>
EMOJI My verdict: <b>VERDICT</b> with <b>CONFIDENCE confidence</b>

🧾 Summary:
<1-2 short sentences>

🧠 Reasons:
• <reason under 100 chars>
• <reason under 100 chars>
• <reason under 100 chars if needed>

🔗 Sources:
• <a href="URL">title under 50 chars</a>
• <a href="URL">title under 50 chars</a>

Limits:
- 1 to 3 reasons.
- 1 to 5 sources.
- Keep titles short and clean.
- Do not mention browser_search.

If input is invalid, answer exactly:
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
                "content": LLM_INSTRUCTIONS
              },
              {
                "role": "user",
                "content": text
              }
            ],
            temperature=LLM_TEMPERATURE,
            max_completion_tokens=LLM_MAX_COMPLETION_TOKENS,
            top_p=LLM_TOP_P,
            reasoning_effort=LLM_REASONING_EFFORT,
            stream=LLM_STREAM,
            stop=None
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
