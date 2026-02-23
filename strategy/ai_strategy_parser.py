"""
Antigravity Trading — AI Strategy Parser
==========================================
Uses Google Gemini to parse plain-English strategy descriptions
into structured StrategyConfig objects.

Usage:
    parser = AIStrategyParser()
    config = parser.parse("Sell ATM straddle at 9:20 with 20% SL on close basis, exit at 15:15")
    print(config.summary())
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import os

import httpx

from strategy.strategy_config import StrategyConfig, LegConfig

logger = logging.getLogger("antigravity.ai_parser")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SYSTEM_PROMPT = """You are a NIFTY options strategy parser. Convert plain-English strategy descriptions into JSON.

AVAILABLE DATA:
- Strikes: ATM, ATM+1 to ATM+10, ATM-1 to ATM-10
- Types: CE (Call), PE (Put)
- Actions: BUY or SELL
- Timeframe: 1-minute candles, 09:15 to 15:30 IST
- NIFTY lot size: 25

OUTPUT FORMAT (JSON only, no markdown):
{
  "name": "Strategy Name",
  "legs": [
    {"action": "SELL", "strike": "ATM", "option_type": "CE", "lots": 1},
    {"action": "SELL", "strike": "ATM", "option_type": "PE", "lots": 1}
  ],
  "entry_time": "09:20",
  "exit_time": "15:15",
  "sl_pct": 25.0,
  "sl_type": "hard",
  "target_pct": 0,
  "target_type": "hard",
  "lot_size": 25,
  "description": "Brief description of the strategy"
}

RULES:
- "straddle" = sell/buy both ATM CE and ATM PE
- "strangle" = sell/buy OTM CE and OTM PE (e.g., ATM+2 CE + ATM-2 PE)
- "iron condor" = sell OTM strangle + buy further OTM strangle for protection
- "bull call spread" = buy ATM CE + sell ATM+2 CE
- "bear put spread" = buy ATM PE + sell ATM-2 PE
- Default entry: 09:20, default exit: 15:15
- Default SL: 25% hard
- "close basis" or "close SL" → sl_type: "close"
- "hard SL" → sl_type: "hard"
- If user says "15% SL", that means sl_pct: 15
- If user says "buy", action is BUY. If "sell", action is SELL
- ATM+1 means 1 strike above ATM (higher strike for CE, also for PE)
- ATM-1 means 1 strike below ATM

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation, no code blocks."""


class AIStrategyParser:
    """Parse plain-English strategy descriptions using Gemini AI."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def parse(self, description: str) -> Optional[StrategyConfig]:
        """
        Parse a plain-English strategy description into StrategyConfig.

        Args:
            description: Strategy in plain English, e.g.
                "Sell ATM straddle at 9:20 with 20% SL on close basis, exit at 15:15"

        Returns:
            StrategyConfig or None on failure
        """
        try:
            # Call Gemini API
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{SYSTEM_PROMPT}\n\nParse this strategy:\n{description}"}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                    "responseMimeType": "application/json",
                },
            }

            resp = httpx.post(
                f"{self.url}?key={self.api_key}",
                json=payload,
                timeout=30,
            )

            if resp.status_code != 200:
                logger.error(f"Gemini API error: {resp.status_code} - {resp.text[:200]}")
                return None

            # Extract response text
            result = resp.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]

            # Clean up response (remove markdown code blocks if present)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            # Parse JSON
            data = json.loads(text)

            # Build StrategyConfig
            config = StrategyConfig.from_dict(data)

            # Validate
            errors = config.validate()
            if errors:
                logger.warning(f"Validation errors: {errors}")
                # Try to fix common issues
                for leg in config.legs:
                    if leg.option_type in ("CALL", "call"):
                        leg.option_type = "CE"
                    elif leg.option_type in ("PUT", "put"):
                        leg.option_type = "PE"
                    if leg.action.upper() not in ("BUY", "SELL"):
                        leg.action = leg.action.upper()

            return config

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"AI parser error: {e}")
            return None

    def parse_with_raw(self, description: str) -> tuple[Optional[StrategyConfig], str]:
        """Parse and also return the raw JSON for display."""
        try:
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{SYSTEM_PROMPT}\n\nParse this strategy:\n{description}"}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                    "responseMimeType": "application/json",
                },
            }

            resp = httpx.post(
                f"{self.url}?key={self.api_key}",
                json=payload,
                timeout=30,
            )

            if resp.status_code != 200:
                return None, f"API Error: {resp.status_code}"

            result = resp.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0].strip()

            data = json.loads(text)
            config = StrategyConfig.from_dict(data)
            return config, json.dumps(data, indent=2)

        except Exception as e:
            return None, f"Error: {e}"


# =========================================================================
# Demo
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AI STRATEGY PARSER DEMO")
    print("=" * 60)

    parser = AIStrategyParser()

    test_cases = [
        "Sell ATM straddle at 9:20 with 20% SL on close basis, exit at 15:15",
        "Buy ATM+2 CE at 9:16 with 30% target and 15% hard stoploss, exit at 14:30",
        "Sell ATM strangle using ATM+3 CE and ATM-3 PE, entry at 9:30, 25% SL hard, no target",
        "Iron condor: sell ATM+2 CE and ATM-2 PE, buy ATM+5 CE and ATM-5 PE, entry 10:00, exit 15:00, 50% SL close",
    ]

    for desc in test_cases:
        print(f"\nInput: {desc}")
        config, raw_json = parser.parse_with_raw(desc)
        if config:
            print(config.summary())
        else:
            print(f"  FAILED: {raw_json}")
        print("-" * 60)
