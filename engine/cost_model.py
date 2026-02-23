"""
Antigravity Trading — Cost Model
==================================
Calculates trading costs: slippage, brokerage, taxes.
Tax rates are date-configurable since govt changes them periodically.

Tax Structure (Options — NSE FNO):
- STT (Securities Transaction Tax)
- GST (on brokerage + exchange charges)
- Exchange Transaction Charges
- SEBI Turnover Fee
- Stamp Duty
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# =========================================================================
# Historical Tax Rate Schedule
# =========================================================================
# Each entry: (effective_from_date, rate_dict)
# When govt changes rates, add a new entry here.

TAX_SCHEDULES = [
    # Before Oct 2024
    {
        "effective_from": date(2020, 1, 1),
        "stt_sell_pct": 0.0625,          # % on sell-side premium (options)
        "stt_buy_pct": 0.0,              # No STT on buy side before Oct 2024
        "exchange_charges_pct": 0.0495,  # NSE FNO transaction charge %
        "sebi_fee_pct": 0.0001,          # SEBI turnover fee %
        "gst_pct": 18.0,                 # GST on (brokerage + exchange charges)
        "stamp_duty_pct": 0.003,         # Stamp duty % (buy side only)
    },
    # After Oct 1, 2024 — STT doubled on options
    {
        "effective_from": date(2024, 10, 1),
        "stt_sell_pct": 0.1,             # Increased from 0.0625% to 0.1%
        "stt_buy_pct": 0.1,             # STT now on buy side too
        "exchange_charges_pct": 0.0495,
        "sebi_fee_pct": 0.0001,
        "gst_pct": 18.0,
        "stamp_duty_pct": 0.003,
    },
]


def get_tax_rates(trade_date: date) -> dict:
    """Get applicable tax rates for a given trade date."""
    applicable = TAX_SCHEDULES[0]
    for schedule in TAX_SCHEDULES:
        if trade_date >= schedule["effective_from"]:
            applicable = schedule
    return applicable


# =========================================================================
# Cost Model
# =========================================================================

@dataclass
class CostConfig:
    """User-adjustable cost parameters."""
    slippage_pts: float = 0.5       # Slippage in points per leg
    brokerage_per_order: float = 20.0   # ₹ per order (flat fee brokers)
    use_taxes: bool = True           # Apply taxes
    custom_tax_rates: Optional[dict] = None  # Override tax rates if needed


@dataclass
class TradeCost:
    """Breakdown of costs for a single trade (entry + exit)."""
    slippage: float = 0.0
    brokerage: float = 0.0
    stt: float = 0.0
    exchange_charges: float = 0.0
    sebi_fee: float = 0.0
    gst: float = 0.0
    stamp_duty: float = 0.0

    @property
    def total(self) -> float:
        return (self.slippage + self.brokerage + self.stt +
                self.exchange_charges + self.sebi_fee +
                self.gst + self.stamp_duty)

    def to_dict(self) -> dict:
        return {
            "slippage": round(self.slippage, 2),
            "brokerage": round(self.brokerage, 2),
            "stt": round(self.stt, 2),
            "exchange_charges": round(self.exchange_charges, 2),
            "sebi_fee": round(self.sebi_fee, 2),
            "gst": round(self.gst, 2),
            "stamp_duty": round(self.stamp_duty, 2),
            "total": round(self.total, 2),
        }


class CostModel:
    """
    Calculate all trading costs for options trades.

    Usage:
        model = CostModel(CostConfig(slippage_pts=1.0, brokerage_per_order=20))
        cost = model.calculate(
            trade_date=date(2025, 6, 15),
            action="SELL",
            premium=150.0,
            quantity=25,
            num_legs=2,
        )
        print(f"Total cost: Rs.{cost.total:.2f}")
    """

    def __init__(self, config: Optional[CostConfig] = None):
        self.config = config or CostConfig()

    def calculate(
        self,
        trade_date: date,
        action: str,           # "BUY" or "SELL"
        premium: float,        # Entry premium per unit
        exit_premium: float = 0.0,  # Exit premium per unit
        quantity: int = 25,    # Total quantity (lots * lot_size)
        num_legs: int = 1,     # Number of strategy legs
    ) -> TradeCost:
        """
        Calculate costs for a round-trip (entry + exit) trade.

        Args:
            trade_date: Date of trade (for tax rate lookup)
            action: BUY or SELL
            premium: Entry premium per unit
            exit_premium: Exit premium per unit
            quantity: Total quantity
            num_legs: Number of legs in the strategy
        """
        cost = TradeCost()

        # 1. Slippage (both entry and exit, per leg)
        cost.slippage = self.config.slippage_pts * quantity * num_legs * 2

        # 2. Brokerage (per order: entry + exit for each leg)
        num_orders = num_legs * 2  # entry + exit
        cost.brokerage = self.config.brokerage_per_order * num_orders

        if not self.config.use_taxes:
            return cost

        # Get applicable tax rates
        rates = (self.config.custom_tax_rates
                 if self.config.custom_tax_rates
                 else get_tax_rates(trade_date))

        # Turnover for charges
        entry_turnover = premium * quantity * num_legs
        exit_turnover = exit_premium * quantity * num_legs
        total_turnover = entry_turnover + exit_turnover

        # 3. STT
        if action == "SELL":
            # Sell side: STT on sell premium
            cost.stt = (entry_turnover * rates["stt_sell_pct"] / 100 +
                        exit_turnover * rates.get("stt_buy_pct", 0) / 100)
        else:
            # Buy side
            cost.stt = (entry_turnover * rates.get("stt_buy_pct", 0) / 100 +
                        exit_turnover * rates["stt_sell_pct"] / 100)

        # 4. Exchange transaction charges (on total turnover)
        cost.exchange_charges = total_turnover * rates["exchange_charges_pct"] / 100

        # 5. SEBI turnover fee
        cost.sebi_fee = total_turnover * rates["sebi_fee_pct"] / 100

        # 6. GST (18% on brokerage + exchange charges)
        gst_base = cost.brokerage + cost.exchange_charges + cost.sebi_fee
        cost.gst = gst_base * rates["gst_pct"] / 100

        # 7. Stamp duty (on buy side only)
        buy_turnover = entry_turnover if action == "BUY" else exit_turnover
        cost.stamp_duty = buy_turnover * rates["stamp_duty_pct"] / 100

        return cost


# =========================================================================
# Demo
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("COST MODEL DEMO")
    print("=" * 60)

    model = CostModel(CostConfig(slippage_pts=0.5, brokerage_per_order=20))

    # Example: Sell ATM straddle, entry at 150 CE + 150 PE, exit at 100 CE + 100 PE
    print("\n--- ATM Straddle Sell (Entry: 150, Exit: 100) ---")

    # CE leg
    ce_cost = model.calculate(
        trade_date=date(2025, 6, 15),
        action="SELL", premium=150.0, exit_premium=100.0,
        quantity=25, num_legs=1,
    )
    # PE leg
    pe_cost = model.calculate(
        trade_date=date(2025, 6, 15),
        action="SELL", premium=150.0, exit_premium=100.0,
        quantity=25, num_legs=1,
    )

    # Full strategy cost
    strategy_cost = model.calculate(
        trade_date=date(2025, 6, 15),
        action="SELL", premium=150.0, exit_premium=100.0,
        quantity=25, num_legs=2,
    )

    print(f"  Gross P&L: Rs.{(150-100)*25*2:,.0f}")
    for k, v in strategy_cost.to_dict().items():
        print(f"  {k:<20s}: Rs.{v:,.2f}")
    print(f"  Net P&L:   Rs.{(150-100)*25*2 - strategy_cost.total:,.2f}")

    # Same trade post Oct 2024 (higher STT)
    print("\n--- Same trade POST Oct 2024 (higher STT) ---")
    strategy_cost_new = model.calculate(
        trade_date=date(2025, 1, 15),
        action="SELL", premium=150.0, exit_premium=100.0,
        quantity=25, num_legs=2,
    )
    for k, v in strategy_cost_new.to_dict().items():
        print(f"  {k:<20s}: Rs.{v:,.2f}")
    print(f"  Net P&L:   Rs.{(150-100)*25*2 - strategy_cost_new.total:,.2f}")
