from aiogram.types import Message

from core.implementations.command import BaseCommand


class StartCommand(BaseCommand):
    name = "start"
    description = "Start the bot and get instructions of use"

    async def execute(self, message: Message) -> None:
        await message.reply(
            text=(
                f"👋 Hello! Welcome to News Checker Telegram Bot!\n\n"
                
                "I'm here to help you to determine which news or articles are fake or real! ✅\n\n"
                
                "🤖 All you need: just send the content of the article, its title or any fact - and I will tell "
                "you the probability of truthfulness with references, facts, etc.\n\n"
                
                "⚠️ Notice that you can send only 7 requests per hour to avoid limit restrictions by AI assistant!"
            )
        )
