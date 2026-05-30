import json
from app.config import settings
from app.ai.schemas import AIDecision

async def ask_openai(signal: dict) -> AIDecision:
    if not settings.ai_openai_enabled or not settings.openai_api_key:
        return AIDecision(engine='openai', direction=signal['direction'], confidence=signal['confidence'], reason='OpenAI disabled; using rule signal', weight=0.5)
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = f"""Return JSON only. Given this crypto trade setup, choose LONG, SHORT, or SKIP.
Signal: {json.dumps(signal)}
Schema: {{"direction":"LONG|SHORT|SKIP","confidence":0.0,"reason":"short"}}"""
    res = await client.chat.completions.create(model='gpt-4o-mini', messages=[{'role':'user','content':prompt}], temperature=0.1)
    data = json.loads(res.choices[0].message.content)
    return AIDecision(engine='openai', direction=data['direction'], confidence=float(data['confidence']), reason=data.get('reason',''), weight=1.0)
