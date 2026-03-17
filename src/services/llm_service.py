"""LLM Service using Google Gemini for AI-powered insights."""

import logging
import json
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)


class GeminiLLMService:
    """LLM service using Google Gemini for portfolio analysis insights."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """Initialize Gemini LLM service.

        Args:
            api_key: Google Gemini API key.
            model_name: Gemini model to use.
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.available = True
            logger.info(f"Gemini LLM service initialized with model: {model_name}")
        except ImportError:
            logger.error("google-generativeai package not installed. Run: pip install google-generativeai")
            self.model = None
            self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None
            self.available = False

    def _generate(self, prompt: str, max_tokens: int = 2048) -> Optional[str]:
        """Generate a response from Gemini.

        Args:
            prompt: The prompt text.
            max_tokens: Maximum tokens in response.

        Returns:
            Generated text or None on failure.
        """
        if not self.available or not self.model:
            logger.warning("Gemini LLM not available")
            return None

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.3,
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None

    def generate_portfolio_insights(self, portfolio_summary: Dict,
                                     risk_analysis: Optional[Dict] = None) -> Optional[str]:
        """Generate AI insights about the portfolio.

        Args:
            portfolio_summary: Portfolio summary dict.
            risk_analysis: Optional risk analysis results.

        Returns:
            AI-generated insights string.
        """
        prompt = f"""You are a professional financial analyst. Analyze this portfolio and provide actionable insights.

IMPORTANT: Base your analysis ONLY on the data provided. Do NOT fabricate numbers, prices, or statistics.
If data is insufficient, say so explicitly.

Portfolio Summary:
{json.dumps(portfolio_summary, indent=2, default=str)}
"""
        if risk_analysis:
            # Only include key metrics, not the full correlation matrix
            risk_summary = {
                k: v for k, v in risk_analysis.items()
                if k != "correlation_matrix" and k != "asset_metrics"
            }
            prompt += f"""
Risk Analysis Results:
{json.dumps(risk_summary, indent=2, default=str)}
"""

        prompt += """
Provide a concise analysis covering:
1. Portfolio composition assessment
2. Key risk factors identified from the data
3. Diversification quality
4. 2-3 specific actionable recommendations

Keep the response under 300 words. Use precise numbers from the data provided."""

        return self._generate(prompt)

    def provide_risk_advice(self, risk_metrics: Dict) -> Optional[str]:
        """Provide AI-powered risk advice based on metrics.

        Args:
            risk_metrics: Risk metrics dictionary.

        Returns:
            AI-generated risk advice.
        """
        prompt = f"""You are a risk management specialist. Analyze these portfolio risk metrics 
and provide professional advice.

IMPORTANT: Use ONLY the numbers provided. Do not invent additional data.

Risk Metrics:
{json.dumps(risk_metrics, indent=2, default=str)}

Provide:
1. Risk level assessment with reasoning based on the metrics above
2. Key concerns (cite specific metric values)
3. Risk mitigation strategies
4. Suggested risk limits

Keep the response under 250 words. Be specific and reference the actual numbers."""

        return self._generate(prompt)

    def generate_rebalancing_recommendations(
        self,
        portfolio_summary: Dict,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        risk_analysis: Optional[Dict] = None,
    ) -> Optional[str]:
        """Generate AI-powered rebalancing recommendations.

        Args:
            portfolio_summary: Portfolio summary dict.
            current_allocation: Current allocation by asset type.
            target_allocation: Target allocation by asset type.
            risk_analysis: Optional risk analysis for context.

        Returns:
            AI-generated rebalancing recommendations.
        """
        prompt = f"""You are a portfolio manager. Provide rebalancing recommendations.

IMPORTANT: Base recommendations ONLY on the data provided. Do not fabricate prices or values.

Portfolio: {json.dumps(portfolio_summary, indent=2, default=str)}

Current Allocation: {json.dumps(current_allocation, indent=2)}
Target Allocation: {json.dumps(target_allocation, indent=2)}
"""
        if risk_analysis:
            risk_summary = risk_analysis.get("risk_summary", {})
            prompt += f"\nRisk Summary: {json.dumps(risk_summary, indent=2, default=str)}"

        prompt += """

Provide:
1. Priority trades to execute (most impactful first)
2. Reasoning for each recommendation
3. Implementation timeline suggestion
4. Any tax considerations to be aware of

Keep the response under 300 words. Be specific about which asset types to adjust."""

        return self._generate(prompt)
