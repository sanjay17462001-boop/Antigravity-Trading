"""
Antigravity Trading — Strategy Configuration
==============================================
Dataclass-based configuration for options strategies.
Supports multi-leg strategies with per-leg strike, type, and action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LegConfig:
    """Configuration for a single strategy leg."""
    action: str          # "BUY" or "SELL"
    strike: str          # "ATM", "ATM+1", "ATM-2", etc.
    option_type: str     # "CE" or "PE"
    lots: int = 1        # Number of lots
    sl_pct: Optional[float] = None       # Per-leg SL % (overrides strategy-level)
    target_pct: Optional[float] = None   # Per-leg target % (overrides strategy-level)

    def sl_price(self, entry_price: float) -> Optional[float]:
        """Calculate SL price from entry price."""
        if self.sl_pct is None:
            return None
        if self.action == "SELL":
            return entry_price * (1 + self.sl_pct / 100)
        else:
            return entry_price * (1 - self.sl_pct / 100)

    def target_price(self, entry_price: float) -> Optional[float]:
        """Calculate target price from entry price."""
        if self.target_pct is None:
            return None
        if self.action == "SELL":
            return entry_price * (1 - self.target_pct / 100)
        else:
            return entry_price * (1 + self.target_pct / 100)


@dataclass
class StrategyConfig:
    """
    Complete strategy configuration.

    Example:
        ATM Straddle Sell at 9:20 with 20% SL on close basis, exit at 15:15
        StrategyConfig(
            name="ATM Straddle Sell",
            legs=[
                LegConfig("SELL", "ATM", "CE"),
                LegConfig("SELL", "ATM", "PE"),
            ],
            entry_time="09:20",
            exit_time="15:15",
            sl_pct=20.0,
            sl_type="close",
        )
    """
    name: str = "Unnamed Strategy"
    legs: list[LegConfig] = field(default_factory=list)

    # Timing
    entry_time: str = "09:20"     # HH:MM — uses OPEN of this candle
    exit_time: str = "15:15"      # HH:MM — uses OPEN of this candle

    # Stop Loss
    sl_pct: float = 0.0           # % SL on each leg premium (0 = no SL)
    sl_type: str = "hard"         # "hard" = exit at SL price if high/low breaches
                                  # "close" = exit at candle close if close breaches

    # Target
    target_pct: float = 0.0       # % target on each leg premium (0 = no target)
    target_type: str = "hard"     # "hard" or "close"

    # Position sizing
    lot_size: int = 25            # NIFTY lot size (currently 25)

    # Filters
    vix_min: Optional[float] = None   # Skip days where VIX < this
    vix_max: Optional[float] = None   # Skip days where VIX > this
    dte_min: Optional[int] = None     # Skip if days-to-expiry < this
    dte_max: Optional[int] = None     # Skip if days-to-expiry > this

    # Expiry
    expiry_type: str = "MONTH"    # "WEEK" or "MONTH"

    # Metadata
    description: str = ""
    version: str = "1.0"
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of errors (empty = valid)."""
        errors = []
        if not self.legs:
            errors.append("At least one leg is required")
        for i, leg in enumerate(self.legs):
            if leg.action not in ("BUY", "SELL"):
                errors.append(f"Leg {i+1}: action must be BUY or SELL")
            if leg.option_type not in ("CE", "PE"):
                errors.append(f"Leg {i+1}: option_type must be CE or PE")
            if not leg.strike.startswith("ATM"):
                errors.append(f"Leg {i+1}: strike must be ATM, ATM+N, or ATM-N")
        if self.sl_type not in ("hard", "close"):
            errors.append("sl_type must be 'hard' or 'close'")
        if self.target_type not in ("hard", "close"):
            errors.append("target_type must be 'hard' or 'close'")
        try:
            h, m = self.entry_time.split(":")
            int(h); int(m)
        except Exception:
            errors.append("entry_time must be HH:MM format")
        try:
            h, m = self.exit_time.split(":")
            int(h); int(m)
        except Exception:
            errors.append("exit_time must be HH:MM format")
        return errors

    def to_dict(self) -> dict:
        """Serialize to dict (for JSON/API)."""
        return {
            "name": self.name,
            "legs": [
                {
                    "action": l.action,
                    "strike": l.strike,
                    "option_type": l.option_type,
                    "lots": l.lots,
                    "sl_pct": l.sl_pct,
                    "target_pct": l.target_pct,
                }
                for l in self.legs
            ],
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "sl_pct": self.sl_pct,
            "sl_type": self.sl_type,
            "target_pct": self.target_pct,
            "target_type": self.target_type,
            "lot_size": self.lot_size,
            "vix_min": self.vix_min,
            "vix_max": self.vix_max,
            "dte_min": self.dte_min,
            "dte_max": self.dte_max,
            "expiry_type": self.expiry_type,
            "description": self.description,
            "version": self.version,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyConfig":
        """Deserialize from dict."""
        legs = [
            LegConfig(
                action=l["action"],
                strike=l["strike"],
                option_type=l["option_type"],
                lots=l.get("lots", 1),
                sl_pct=l.get("sl_pct"),
                target_pct=l.get("target_pct"),
            )
            for l in d.get("legs", [])
        ]
        return cls(
            name=d.get("name", "Unnamed"),
            legs=legs,
            entry_time=d.get("entry_time", "09:20"),
            exit_time=d.get("exit_time", "15:15"),
            sl_pct=d.get("sl_pct", 0.0),
            sl_type=d.get("sl_type", "hard"),
            target_pct=d.get("target_pct", 0.0),
            target_type=d.get("target_type", "hard"),
            lot_size=d.get("lot_size", 25),
            vix_min=d.get("vix_min"),
            vix_max=d.get("vix_max"),
            dte_min=d.get("dte_min"),
            dte_max=d.get("dte_max"),
            expiry_type=d.get("expiry_type", "MONTH"),
            description=d.get("description", ""),
            version=d.get("version", "1.0"),
            params=d.get("params", {}),
        )

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [f"Strategy: {self.name}"]
        for i, leg in enumerate(self.legs):
            sl = f", SL={leg.sl_pct}%" if leg.sl_pct else ""
            tgt = f", TGT={leg.target_pct}%" if leg.target_pct else ""
            lines.append(f"  Leg {i+1}: {leg.action} {leg.strike} {leg.option_type} x{leg.lots}{sl}{tgt}")
        lines.append(f"  Entry: {self.entry_time} | Exit: {self.exit_time}")
        if self.sl_pct:
            lines.append(f"  SL: {self.sl_pct}% ({self.sl_type})")
        if self.target_pct:
            lines.append(f"  Target: {self.target_pct}% ({self.target_type})")
        if self.vix_min or self.vix_max:
            lines.append(f"  VIX filter: {self.vix_min or '-'} to {self.vix_max or '-'}")
        return "\n".join(lines)
