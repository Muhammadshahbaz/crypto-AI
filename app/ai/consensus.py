from app.config import settings
from app.ai.openai_engine import ask_openai
from app.ai.claude_engine import ask_claude

async def get_consensus(signal: dict) -> dict:
    decisions = [await ask_openai(signal), await ask_claude(signal)]
    scores = {'LONG': 0.0, 'SHORT': 0.0, 'SKIP': 0.0}
    total_weight = sum(d.weight for d in decisions) or 1.0
    for d in decisions:
        scores[d.direction] = scores.get(d.direction, 0.0) + d.weight * d.confidence
    direction = max(scores, key=scores.get)
    consensus_score = scores[direction] / total_weight
    return {
        'direction': direction if consensus_score >= settings.consensus_threshold else 'SKIP',
        'consensus_score': float(consensus_score),
        'decisions': [d.model_dump() for d in decisions]
    }
