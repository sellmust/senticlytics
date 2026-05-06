"""
Gemini Service
Integration with Google Gemini API for advanced feedback analysis.
Supports bilingual feedback (Indonesian + English).
"""

import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configuration
GEMINI_API_KEY    = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL      = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', 0.3))
GEMINI_MAX_TOKENS  = int(os.getenv('GEMINI_MAX_TOKENS', 1024))
GEMINI_TOP_P       = float(os.getenv('GEMINI_TOP_P', 0.95))
GEMINI_TOP_K       = int(os.getenv('GEMINI_TOP_K', 40))

if not GEMINI_API_KEY:
    logger.warning("⚠ GEMINI_API_KEY not set")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SENTIMENT_ANALYSIS_PROMPT = """
You are a customer service response model. Analyze the sentiment of the following customer feedback.
The feedback may be in Indonesian or English — handle both.

Based on the sentiment, generate an appropriate, personalized response that directly addresses the content of the feedback:
- If sentiment is "negative": respond with a sincere apology that acknowledges the specific issue and offer a concrete helpful solution.
- If sentiment is "neutral": respond with a polite thank-you that references the specific feedback content.
- If sentiment is "positive": respond with a warm thank-you and appreciation that echoes the positive aspects mentioned.

The response must feel natural and specific — NOT a generic template.

Return a JSON object with EXACTLY these fields:
{{
  "sentiment": "positive" | "neutral" | "negative",
  "sentiment_respon": "<personalized response message in the same language as the feedback>"
}}

Feedback: {text}

Return ONLY valid JSON. No markdown, no explanation outside JSON.
"""

SENTIMENT_WITH_CONTEXT_PROMPT = """
You are a customer service response model. Analyze the sentiment of the following customer feedback.
The feedback may be in Indonesian or English — handle both.

Below are similar past feedbacks and how they were handled (for context):
{rag_context}

Based on the sentiment AND the context above, generate a personalized and specific response:
- If sentiment is "negative": acknowledge the exact problem, apologize sincerely, and offer a concrete solution.
- If sentiment is "neutral": thank the customer and reference what they specifically mentioned.
- If sentiment is "positive": warmly thank the customer and echo the specific positive aspects they raised.

Return a JSON object with EXACTLY these fields:
{{
  "sentiment": "positive" | "neutral" | "negative",
  "sentiment_respon": "<personalized response message in the same language as the feedback>"
}}

Current Feedback: {text}

Return ONLY valid JSON. No markdown, no explanation outside JSON.
"""

INSIGHT_GENERATION_PROMPT = """
You are a customer experience analyst. Based on the following customer feedbacks from the past day,
generate actionable insights for the business team.

The feedbacks may be in Indonesian or English.

Return a JSON object with EXACTLY these fields:
{{
  "insights": [
    {{
      "title": "<short title>",
      "description": "<1-2 sentence description>",
      "impact": "high" | "medium" | "low",
      "priority": 1-5
    }}
  ],
  "recommendations": ["<actionable recommendation string>"],
  "trends": ["<observed pattern or trend>"],
  "critical_issues": ["<issue that needs immediate attention, if any>"]
}}

Generate 3-5 insights, 2-4 recommendations, 2-3 trends.

Feedbacks:
{feedbacks_text}

Return ONLY valid JSON. No markdown, no explanation outside JSON.
"""

# ---------------------------------------------------------------------------
# Gemini Service
# ---------------------------------------------------------------------------
class GeminiService:
    """Service for Gemini API interactions — sentiment, insights"""
    def __init__(self):
        try:
            genai.configure(api_key=GEMINI_API_KEY, transport='rest')
            self.model = genai.GenerativeModel(model_name=GEMINI_MODEL)
            self.generation_config = genai.types.GenerationConfig(
                temperature=float(GEMINI_TEMPERATURE),
                top_p=float(GEMINI_TOP_P),
                top_k=int(GEMINI_TOP_K),
                max_output_tokens=int(GEMINI_MAX_TOKENS),
                candidate_count=1
            )
            logger.info(f"✓ Gemini service initialized: {GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini service: {str(e)}")
            self.model = None

    def _safe_generate(self, prompt: str, config=None) -> Optional[str]:
        """Generate content with error handling"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=config or self.generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"❌ Gemini generate error: {str(e)}")
            return None

    def _extract_json(self, raw: str) -> Optional[Dict]:
        """Safely parse JSON from Gemini response"""
        try:
            clean = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            logger.warning(f"⚠ JSON parse failed: {str(e)}")
            return None

    # -----------------------------------------------------------------------
    # Sentiment Analysis (with optional RAG context)
    # -----------------------------------------------------------------------
    async def analyze_sentiment(self, text: str, rag_context: Optional[str] = None) -> Dict:
        """
        Analyze sentiment of a single feedback text.
        Supports Indonesian and English.

        If rag_context is provided (retrieved similar feedbacks), Gemini uses it
        to generate a more relevant and personalized sentiment_respon.

        Returns:
            {sentiment, sentiment_respon}
        """
        if not text or not text.strip():
            return {'sentiment': 'neutral', 'sentiment_respon': 'Terima kasih atas ulasan Anda.'}

        if rag_context:
            prompt = SENTIMENT_WITH_CONTEXT_PROMPT.format(
                text=text[:1000],
                rag_context=rag_context
            )
        else:
            prompt = SENTIMENT_ANALYSIS_PROMPT.format(text=text[:1000])

        raw = self._safe_generate(prompt)

        if raw:
            result = self._extract_json(raw)
            if result and 'sentiment' in result:
                logger.info(f"✓ Sentiment: {result['sentiment']}")
                return result

        return self._fallback_sentiment(text)

    async def batch_analyze_sentiment(self, texts: List[str]) -> List[Dict]:
        """Analyze sentiment for a list of texts (no RAG context in batch)"""
        results = []
        for text in texts:
            result = await self.analyze_sentiment(text)
            results.append(result)
        return results

    async def analyze_feedback(self, text: str, rag_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Full feedback analysis: sentiment + personalized response.
        Uses RAG context if provided.
        """
        if not self.model:
            return self._fallback_sentiment(text)

        return await self.analyze_sentiment(text, rag_context=rag_context)

    def _fallback_sentiment(self, text: str) -> Dict:
        """Rule-based fallback if Gemini fails — returns neutral template only"""
        text_lower = text.lower()
        if any(w in text_lower for w in ['bagus', 'good', 'great', 'love', 'mantap', 'puas', 'recommended']):
            sentiment = 'positive'
        elif any(w in text_lower for w in ['jelek', 'bad', 'terrible', 'kecewa', 'rusak', 'lambat', 'mahal']):
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        return {
            'sentiment': sentiment,
            'sentiment_respon': 'Terima kasih atas ulasan Anda. Tim kami akan segera menindaklanjuti.'
        }

    # -----------------------------------------------------------------------
    # Insight Generation
    # -----------------------------------------------------------------------
    async def generate_insights(self, feedbacks: List[Dict]) -> Dict:
        """
        Generate actionable insights from a list of feedbacks.
        Called by the n8n pipeline every 6 hours (or daily).

        Args:
            feedbacks: list of dicts with keys: text, sentiment, rating, category

        Returns:
            {insights, recommendations, trends, critical_issues}
        """
        if not feedbacks:
            return {'insights': [], 'recommendations': [], 'trends': [], 'critical_issues': []}

        feedbacks_text = "\n".join([
            f"[{f.get('sentiment', '?').upper()} | {f.get('category', 'general')} | rating:{f.get('rating', '?')}] {f.get('text', '')[:200]}"
            for f in feedbacks[:20]
        ])

        prompt = INSIGHT_GENERATION_PROMPT.format(feedbacks_text=feedbacks_text)
        raw = self._safe_generate(prompt)

        if raw:
            result = self._extract_json(raw)
            if result and 'insights' in result:
                logger.info(f"✓ Insights generated: {len(result['insights'])} insights")
                return result

        return {'insights': [], 'recommendations': [], 'trends': [], 'critical_issues': [], 'error': 'Parse failed'}

    # -----------------------------------------------------------------------
    # Response Generation
    # -----------------------------------------------------------------------
    async def generate_response(self, feedback: str, tone: str = "professional") -> str:
        """Generate a customer service reply to a feedback"""
        prompt = f"""Generate a {tone} response to this customer feedback in the same language as the feedback.
Keep it concise (2-3 sentences).

Feedback: {feedback}

Response:"""
        config = genai.types.GenerationConfig(temperature=0.6, max_output_tokens=200)
        raw = self._safe_generate(prompt, config=config)
        return (raw or "").strip()

    # -----------------------------------------------------------------------
    # Custom Analysis
    # -----------------------------------------------------------------------
    async def custom_analysis(self, text: str, analysis_type: str) -> Dict:
        """Run custom analysis: 'urgency'"""
        prompts = {
            "urgency": f"""Assess the urgency of this feedback. Return JSON with:
{{"urgency_level": "critical"|"high"|"medium"|"low", "requires_immediate_action": bool, "recommended_action": str, "escalation_needed": bool}}
Text: {text}\nReturn ONLY valid JSON."""
        }

        if analysis_type not in prompts:
            return {'error': f'Unknown analysis type: {analysis_type}'}

        raw = self._safe_generate(prompts[analysis_type])
        if raw:
            result = self._extract_json(raw)
            if result:
                return result
        return {'error': 'Parse failed'}

    # -----------------------------------------------------------------------
    # Health Check
    # -----------------------------------------------------------------------
    async def health_check(self) -> bool:
        """Ping Gemini API"""
        try:
            config = genai.types.GenerationConfig(max_output_tokens=5)
            self.model.generate_content("Reply with OK", generation_config=config)
            logger.info("✓ Gemini health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Gemini health check failed: {str(e)}")
            return False


# ---------------------------------------------------------------------------
# Global Singleton
# ---------------------------------------------------------------------------
_gemini_service: Optional[GeminiService] = None

async def get_gemini_service() -> GeminiService:
    """Get or initialize global Gemini service instance"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


if __name__ == "__main__":
    import asyncio

    async def test():
        service = GeminiService()

        r1 = await service.analyze_feedback("Pengiriman sangat lambat, barang sampai rusak parah!")
        print("Analysis (negative):", json.dumps(r1, indent=2))

        r2 = await service.analyze_feedback("Produknya bagus banget, recommended!")
        print("Analysis (positive):", json.dumps(r2, indent=2))

        r3 = await service.analyze_feedback("Customer service tidak responsif dan tidak membantu sama sekali")
        print("Analysis (negative - CS):", json.dumps(r3, indent=2))

    asyncio.run(test())