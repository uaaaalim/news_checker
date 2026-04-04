from datetime import datetime, UTC, timedelta
from json import JSONDecodeError

from aiogram.types import Message
from groq import RateLimitError

from core.implementations.message import BaseMessage
from database.services.user_check import get_by_tg_id, delete_oldest_by_tg_id, create_user_check
from services.ai.news_checker import AI_SYSTEM_INSTRUCTIONS

import json


class AnyMessage(BaseMessage):
    trigger = "*"

    LLM_TEMPERATURE = 0.2
    LLM_MAX_COMPLETION_TOKENS = 500
    LLM_STREAM = False
    LLM_TOOLS = [{"type": "browser_search"}]
    LLM_REASONING_EFFORT = "low"
    LLM_TOP_P = 1
    LLM_MODEL = "openai/gpt-oss-120b"
    MAX_TEXT_LENGTH = 1000

    async def handle(self, message: Message) -> None:
        async with self.client.db.session() as db:
            async with db.begin():
                checks = await get_by_tg_id(db, message.from_user.id)
                one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

                for c in checks:
                    if c.date < one_hour_ago:
                        await delete_oldest_by_tg_id(db, c.tg_id)

                checks = await get_by_tg_id(db, message.from_user.id)

                if len(checks) >= 7:
                    oldest = min(checks, key=lambda x: x.date)

                    retry_at = oldest.date + timedelta(hours=1)
                    now = datetime.now(UTC)

                    remaining = retry_at - now

                    seconds = int(remaining.total_seconds())
                    minutes = seconds // 60
                    seconds = seconds % 60

                    await message.reply(
                        f"❌ You've been rate-limited (You've reached 7 requests in 1 hour).\n"
                        f"Try again in {minutes}m {seconds}s"
                    )
                    return

                response = await self.__request_llm(message)

                if response:
                    await create_user_check(db, message.from_user.id, datetime.now(UTC))

    async def __request_llm(self, message: Message) -> bool:
        text = (message.text or "").strip()

        if not text:
            await message.reply(
                text="❌ The message content is empty. Please write something."
            )
            return False

        if len(text) > self.MAX_TEXT_LENGTH:
            await message.reply(
                text=f"❌ The message is too long. Maximum length is {self.MAX_TEXT_LENGTH} characters."
            )
            return False

        status_message = await message.reply(
            text="⏳ Accepted. I'm checking information related to your query. Please wait."
        )

        try:
            completion = await self.client.groq.chat.completions.create(
                model=self.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": AI_SYSTEM_INSTRUCTIONS,
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                temperature=self.LLM_TEMPERATURE,
                max_completion_tokens=self.LLM_MAX_COMPLETION_TOKENS,
                top_p=self.LLM_TOP_P,
                reasoning_effort=self.LLM_REASONING_EFFORT,
                stop=None,
                stream=False,
                tools=self.LLM_TOOLS
            )

            choice = completion.choices[0].message
            content = (choice.content or "").strip()

            if not content:
                self.client.logger.warning("LLM returned empty content: %s", completion)
                await status_message.edit_text(
                    "❌ The model returned an empty response."
                )
                return False

            content = self._clean_json_content(content)
            data = json.loads(content)

        except JSONDecodeError as error:
            self.client.logger.exception("Failed to parse LLM JSON: %s", error)
            await status_message.edit_text(
                "❌ I received an invalid JSON response from the model."
            )
            return False

        except RateLimitError:
            self.client.logger.warning("Rate limit error during the request to LLM")
            await status_message.edit_text(
                "❌ Rate limit error during the request. Please, try again later."
            )
            return False

        except Exception as error:
            self.client.logger.exception("Groq request failed: %s", error)
            await status_message.edit_text(
                "❌ An error occurred while processing your request."
            )
            return False

        headline = data.get("headline", "unknown")
        verdict = data.get("verdict", "unknown")
        confidence = data.get("confidence", "unknown")
        summary = data.get("summary", "No summary was provided.")
        reasons = data.get("reasons", [])
        sources = data.get("sources", [])

        answer = [
            f"📰 <b>Headline:</b> {headline}\n",

            f"📌 So, my verdict: <b>{verdict}</b> (with <b>{confidence} confidence</b>)\n",
            
            f"📰 Summary:",
            f"— {summary}\n"
        ]

        if reasons:
            answer.append("🧠 <b>Reasons:</b>")
            answer.extend(f"• {reason}" for reason in reasons)
            answer.append(" ")

        if sources:
            answer.append("🔗 <b>Sources (references):</b>")
            _sources = []

            for source in sources:
                title = source.get("title", "Untitled")
                url = source.get("url", "")

                if not url:
                    continue

                _sources.append(f"• <a href=\"{url}\">{title}</a>")

                if len(_sources) >= 5:
                    break

            answer.extend(_sources)

        await status_message.edit_text(text="\n".join(answer), disable_web_page_preview=True, parse_mode="HTML")
        return True

    @staticmethod
    def _clean_json_content(content: str) -> str:
        content = content.strip()

        if content.startswith("```json"):
            content = content.removeprefix("```json").strip()
        elif content.startswith("```"):
            content = content.removeprefix("```").strip()

        if content.endswith("```"):
            content = content.removesuffix("```").strip()

        return content
