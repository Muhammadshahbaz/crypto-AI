import httpx
from app.config import settings

async def notify(message: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    url = f'https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage'
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={'chat_id': settings.telegram_chat_id, 'text': message})
