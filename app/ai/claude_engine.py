import json
from app.config import settings
from app.ai.schemas import AIDecision

async def ask_claude(signal: dict) -> AIDecision:
    if not settings.ai_claude_enabled or not settings.anthropic_api_key:
        return AIDecision(engine='claude', direction=signal['direction'], confidence=signal['confidence'], reason='Claude disabled; using rule signal', weight=0.5)
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Return JSON only. Choose LONG, SHORT, or SKIP for this setup.
Signal: {json.dumps(signal)}
Schema: {{"direction":"LONG|SHORT|SKIP","confidence":0.0,"reason":"short"}}"""
    msg = await client.messages.create(model='claude-3-5-sonnet-20241022', max_tokens=300, messages=[{'role':'user','content':prompt}], temperature=0.1)
    data = json.loads(msg.content[0].text)
    return AIDecision(engine='claude', direction=data['direction'], confidence=float(data['confidence']), reason=data.get('reason',''), weight=1.0)
