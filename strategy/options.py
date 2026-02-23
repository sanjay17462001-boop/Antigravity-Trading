"""
Antigravity Trading — Options Greeks Calculator
================================================
Black-Scholes pricing, Greeks, IV computation, and strategy payoff builders.
Supports European options on NSE indices (NIFTY, BANKNIFTY).
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
from scipy.stats import norm
from scipy.optimize import brentq


class OptionType(Enum):
    CALL = "CE"
    PUT = "PE"


class StrategyType(Enum):
    LONG_CALL = "Long Call"
    SHORT_CALL = "Short Call"
    LONG_PUT = "Long Put"
    SHORT_PUT = "Short Put"
    BULL_CALL_SPREAD = "Bull Call Spread"
    BEAR_PUT_SPREAD = "Bear Put Spread"
    STRADDLE = "Straddle"
    STRANGLE = "Strangle"
    IRON_CONDOR = "Iron Condor"
    IRON_BUTTERFLY = "Iron Butterfly"


@dataclass
class Greeks:
    """Option Greeks container."""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0      # per day
    vega: float = 0.0       # per 1% move in IV
    rho: float = 0.0        # per 1% move in rate
    charm: float = 0.0      # delta decay
    vanna: float = 0.0      # delta sensitivity to IV
    volga: float = 0.0      # vega sensitivity to IV


@dataclass
class OptionPrice:
    """Option pricing result."""
    theoretical_price: float
    intrinsic_value: float
    time_value: float
    greeks: Greeks
    iv: Optional[float] = None     # if computed
    moneyness: str = ""             # ITM / ATM / OTM


@dataclass
class OptionLeg:
    """Single leg of an options strategy."""
    option_type: OptionType
    strike: float
    premium: float
    qty: int                         # +ve = long, -ve = short
    lot_size: int = 50               # NIFTY = 50, BANKNIFTY = 15


@dataclass
class StrategyPayoff:
    """Payoff profile of a multi-leg strategy."""
    name: str
    legs: List[OptionLeg]
    spot_range: List[float] = field(default_factory=list)
    payoff_values: List[float] = field(default_factory=list)
    max_profit: float = 0.0
    max_loss: float = 0.0
    breakeven_points: List[float] = field(default_factory=list)
    net_premium: float = 0.0


# =============================================================================
# Black-Scholes Model
# =============================================================================

def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate d1 in Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return 0.0
    return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))


def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate d2 in Black-Scholes formula."""
    if T <= 0 or sigma <= 0:
        return 0.0
    return _d1(S, K, T, r, sigma) - sigma * math.sqrt(T)


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = OptionType.CALL,
) -> float:
    """
    Black-Scholes option price.

    Args:
        S: Spot price (e.g., 25450)
        K: Strike price (e.g., 25500)
        T: Time to expiry in years (e.g., 7/365 for 7 days)
        r: Risk-free rate as decimal (e.g., 0.065 for 6.5%)
        sigma: Volatility as decimal (e.g., 0.14 for 14%)
        option_type: CALL or PUT

    Returns:
        Theoretical option price
    """
    if T <= 0:
        # At expiry
        if option_type == OptionType.CALL:
            return max(S - K, 0)
        else:
            return max(K - S, 0)

    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)

    if option_type == OptionType.CALL:
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return max(price, 0)


# =============================================================================
# Greeks Calculation
# =============================================================================

def calculate_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = OptionType.CALL,
) -> Greeks:
    """
    Calculate all Greeks for an option.

    Returns Greeks with theta in per-day terms and vega per 1% IV move.
    """
    if T <= 0 or sigma <= 0:
        # At expiry — only delta matters
        if option_type == OptionType.CALL:
            delta = 1.0 if S > K else 0.0
        else:
            delta = -1.0 if S < K else 0.0
        return Greeks(delta=delta)

    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(S, K, T, r, sigma)
    sqrt_T = math.sqrt(T)
    n_d1 = norm.pdf(d1)  # standard normal PDF at d1
    exp_rT = math.exp(-r * T)

    # Delta
    if option_type == OptionType.CALL:
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1

    # Gamma (same for call and put)
    gamma = n_d1 / (S * sigma * sqrt_T)

    # Theta (annualized, then convert to per-day)
    common_theta = -(S * n_d1 * sigma) / (2 * sqrt_T)
    if option_type == OptionType.CALL:
        theta_annual = common_theta - r * K * exp_rT * norm.cdf(d2)
    else:
        theta_annual = common_theta + r * K * exp_rT * norm.cdf(-d2)
    theta_daily = theta_annual / 365  # per calendar day

    # Vega (per 1% move in volatility)
    vega = S * sqrt_T * n_d1 / 100  # divide by 100 for per 1%

    # Rho (per 1% move in interest rate)
    if option_type == OptionType.CALL:
        rho = K * T * exp_rT * norm.cdf(d2) / 100
    else:
        rho = -K * T * exp_rT * norm.cdf(-d2) / 100

    # Charm (delta decay per day)
    charm = -n_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T)
    charm /= 365  # per day

    # Vanna (dDelta/dVol)
    vanna = -n_d1 * d2 / sigma

    # Volga (dVega/dVol)
    volga = vega * d1 * d2 / sigma

    return Greeks(
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        theta=round(theta_daily, 2),
        vega=round(vega, 2),
        rho=round(rho, 2),
        charm=round(charm, 6),
        vanna=round(vanna, 4),
        volga=round(volga, 4),
    )


# =============================================================================
# Option Pricing (price + greeks + moneyness)
# =============================================================================

def price_option(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = OptionType.CALL,
) -> OptionPrice:
    """Full option pricing with greeks and moneyness."""
    price = black_scholes_price(S, K, T, r, sigma, option_type)
    greeks = calculate_greeks(S, K, T, r, sigma, option_type)

    if option_type == OptionType.CALL:
        intrinsic = max(S - K, 0)
    else:
        intrinsic = max(K - S, 0)

    time_value = max(price - intrinsic, 0)

    # Moneyness
    pct_diff = (S - K) / K * 100
    if option_type == OptionType.CALL:
        if pct_diff > 1:
            moneyness = "ITM"
        elif pct_diff < -1:
            moneyness = "OTM"
        else:
            moneyness = "ATM"
    else:
        if pct_diff < -1:
            moneyness = "ITM"
        elif pct_diff > 1:
            moneyness = "OTM"
        else:
            moneyness = "ATM"

    return OptionPrice(
        theoretical_price=round(price, 2),
        intrinsic_value=round(intrinsic, 2),
        time_value=round(time_value, 2),
        greeks=greeks,
        iv=round(sigma * 100, 2),  # as percentage
        moneyness=moneyness,
    )


# =============================================================================
# Implied Volatility
# =============================================================================

def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: OptionType = OptionType.CALL,
    precision: float = 1e-6,
) -> Optional[float]:
    """
    Compute implied volatility from market price using Brent's method.

    Args:
        market_price: Observed market price of the option
        S, K, T, r: Spot, strike, time to expiry (years), risk-free rate
        option_type: CALL or PUT

    Returns:
        Implied volatility as decimal (e.g., 0.14 for 14%), or None if not solvable
    """
    if market_price <= 0 or T <= 0:
        return None

    # Intrinsic value check
    if option_type == OptionType.CALL:
        intrinsic = max(S - K * math.exp(-r * T), 0)
    else:
        intrinsic = max(K * math.exp(-r * T) - S, 0)

    if market_price < intrinsic - precision:
        return None  # below intrinsic — arbitrage

    def objective(sigma: float) -> float:
        return black_scholes_price(S, K, T, r, sigma, option_type) - market_price

    try:
        iv = brentq(objective, 0.001, 5.0, xtol=precision, maxiter=200)
        return round(iv, 6)
    except (ValueError, RuntimeError):
        return None


def iv_from_chain(
    spot: float,
    strikes: List[float],
    premiums: List[float],
    T: float,
    r: float = 0.065,
    option_type: OptionType = OptionType.CALL,
) -> List[Tuple[float, Optional[float]]]:
    """
    Compute IV for an entire option chain.

    Returns list of (strike, iv) tuples. IV is None if computation fails.
    """
    results = []
    for strike, premium in zip(strikes, premiums):
        iv = implied_volatility(premium, spot, strike, T, r, option_type)
        results.append((strike, round(iv * 100, 2) if iv else None))
    return results


# =============================================================================
# ATM / Strike Selection
# =============================================================================

def get_atm_strike(spot: float, strike_interval: float = 50) -> float:
    """Get ATM strike rounded to nearest strike interval."""
    return round(spot / strike_interval) * strike_interval


def get_strikes_around_atm(
    spot: float,
    num_strikes: int = 10,
    strike_interval: float = 50,
) -> List[float]:
    """Get strikes around ATM (symmetric)."""
    atm = get_atm_strike(spot, strike_interval)
    half = num_strikes // 2
    return [atm + (i - half) * strike_interval for i in range(num_strikes + 1)]


def select_strike_by_delta(
    spot: float,
    target_delta: float,
    T: float,
    sigma: float,
    r: float = 0.065,
    option_type: OptionType = OptionType.CALL,
    strike_interval: float = 50,
) -> float:
    """Select the strike closest to a target delta."""
    strikes = get_strikes_around_atm(spot, 40, strike_interval)
    best_strike = strikes[0]
    best_diff = float("inf")

    for strike in strikes:
        greeks = calculate_greeks(spot, strike, T, r, sigma, option_type)
        diff = abs(abs(greeks.delta) - abs(target_delta))
        if diff < best_diff:
            best_diff = diff
            best_strike = strike

    return best_strike


# =============================================================================
# Strategy Payoff Builders
# =============================================================================

def compute_payoff(
    legs: List[OptionLeg],
    spot_range: Optional[List[float]] = None,
    spot: Optional[float] = None,
) -> StrategyPayoff:
    """
    Compute payoff profile for a multi-leg options strategy.

    Args:
        legs: List of OptionLeg (qty > 0 = long, qty < 0 = short)
        spot_range: Custom spot prices to evaluate (optional)
        spot: Current spot for auto-generating range (optional)

    Returns:
        StrategyPayoff with payoff values, max profit/loss, breakevens
    """
    if spot_range is None:
        if spot:
            center = spot
        else:
            # Use average of strikes
            center = sum(leg.strike for leg in legs) / len(legs)
        spread = center * 0.08  # +/- 8%
        spot_range = [center - spread + i * (2 * spread / 200) for i in range(201)]

    # Net premium
    net_premium = sum(leg.premium * leg.qty * leg.lot_size for leg in legs)

    payoff_values = []
    for s in spot_range:
        total = 0
        for leg in legs:
            if leg.option_type == OptionType.CALL:
                intrinsic = max(s - leg.strike, 0)
            else:
                intrinsic = max(leg.strike - s, 0)

            # P&L per lot = (intrinsic - premium) * qty * lot_size
            pnl = (intrinsic - leg.premium) * leg.qty * leg.lot_size
            total += pnl
        payoff_values.append(round(total, 2))

    max_profit = max(payoff_values)
    max_loss = min(payoff_values)

    # Find breakeven points (where payoff crosses zero)
    breakevens = []
    for i in range(1, len(payoff_values)):
        if payoff_values[i - 1] * payoff_values[i] < 0:
            # Linear interpolation
            x1, y1 = spot_range[i - 1], payoff_values[i - 1]
            x2, y2 = spot_range[i], payoff_values[i]
            be = x1 - y1 * (x2 - x1) / (y2 - y1)
            breakevens.append(round(be, 2))

    return StrategyPayoff(
        name="Custom",
        legs=legs,
        spot_range=[round(s, 2) for s in spot_range],
        payoff_values=payoff_values,
        max_profit=max_profit,
        max_loss=max_loss,
        breakeven_points=breakevens,
        net_premium=round(net_premium, 2),
    )


# =============================================================================
# Pre-built Strategy Builders
# =============================================================================

def build_straddle(
    spot: float,
    ce_premium: float,
    pe_premium: float,
    is_long: bool = False,
    lot_size: int = 50,
) -> StrategyPayoff:
    """Build a straddle (long or short) at ATM."""
    atm = get_atm_strike(spot)
    q = 1 if is_long else -1
    legs = [
        OptionLeg(OptionType.CALL, atm, ce_premium, q, lot_size),
        OptionLeg(OptionType.PUT, atm, pe_premium, q, lot_size),
    ]
    payoff = compute_payoff(legs, spot=spot)
    payoff.name = f"{'Long' if is_long else 'Short'} Straddle @ {atm}"
    return payoff


def build_strangle(
    spot: float,
    ce_strike: float,
    pe_strike: float,
    ce_premium: float,
    pe_premium: float,
    is_long: bool = False,
    lot_size: int = 50,
) -> StrategyPayoff:
    """Build a strangle."""
    q = 1 if is_long else -1
    legs = [
        OptionLeg(OptionType.CALL, ce_strike, ce_premium, q, lot_size),
        OptionLeg(OptionType.PUT, pe_strike, pe_premium, q, lot_size),
    ]
    payoff = compute_payoff(legs, spot=spot)
    payoff.name = f"{'Long' if is_long else 'Short'} Strangle ({pe_strike}PE / {ce_strike}CE)"
    return payoff


def build_iron_condor(
    spot: float,
    sell_ce_strike: float,
    buy_ce_strike: float,
    sell_pe_strike: float,
    buy_pe_strike: float,
    sell_ce_premium: float,
    buy_ce_premium: float,
    sell_pe_premium: float,
    buy_pe_premium: float,
    lot_size: int = 50,
) -> StrategyPayoff:
    """Build an iron condor (sell inner, buy outer wings)."""
    legs = [
        OptionLeg(OptionType.CALL, sell_ce_strike, sell_ce_premium, -1, lot_size),
        OptionLeg(OptionType.CALL, buy_ce_strike, buy_ce_premium, 1, lot_size),
        OptionLeg(OptionType.PUT, sell_pe_strike, sell_pe_premium, -1, lot_size),
        OptionLeg(OptionType.PUT, buy_pe_strike, buy_pe_premium, 1, lot_size),
    ]
    payoff = compute_payoff(legs, spot=spot)
    payoff.name = f"Iron Condor ({buy_pe_strike}/{sell_pe_strike}PE - {sell_ce_strike}/{buy_ce_strike}CE)"
    return payoff


def build_bull_call_spread(
    spot: float,
    buy_strike: float,
    sell_strike: float,
    buy_premium: float,
    sell_premium: float,
    lot_size: int = 50,
) -> StrategyPayoff:
    """Buy lower strike CE, sell higher strike CE."""
    legs = [
        OptionLeg(OptionType.CALL, buy_strike, buy_premium, 1, lot_size),
        OptionLeg(OptionType.CALL, sell_strike, sell_premium, -1, lot_size),
    ]
    payoff = compute_payoff(legs, spot=spot)
    payoff.name = f"Bull Call Spread ({buy_strike}/{sell_strike})"
    return payoff


def build_bear_put_spread(
    spot: float,
    buy_strike: float,
    sell_strike: float,
    buy_premium: float,
    sell_premium: float,
    lot_size: int = 50,
) -> StrategyPayoff:
    """Buy higher strike PE, sell lower strike PE."""
    legs = [
        OptionLeg(OptionType.PUT, buy_strike, buy_premium, 1, lot_size),
        OptionLeg(OptionType.PUT, sell_strike, sell_premium, -1, lot_size),
    ]
    payoff = compute_payoff(legs, spot=spot)
    payoff.name = f"Bear Put Spread ({sell_strike}/{buy_strike})"
    return payoff


def build_butterfly(
    spot: float,
    lower_strike: float,
    middle_strike: float,
    upper_strike: float,
    lower_premium: float,
    middle_premium: float,
    upper_premium: float,
    lot_size: int = 50,
) -> StrategyPayoff:
    """Long butterfly spread using calls."""
    legs = [
        OptionLeg(OptionType.CALL, lower_strike, lower_premium, 1, lot_size),
        OptionLeg(OptionType.CALL, middle_strike, middle_premium, -2, lot_size),
        OptionLeg(OptionType.CALL, upper_strike, upper_premium, 1, lot_size),
    ]
    payoff = compute_payoff(legs, spot=spot)
    payoff.name = f"Butterfly ({lower_strike}/{middle_strike}/{upper_strike})"
    return payoff


# =============================================================================
# Convenience: Quick option chain pricer
# =============================================================================

def price_chain(
    spot: float,
    strikes: List[float],
    T: float,
    sigma: float,
    r: float = 0.065,
) -> List[dict]:
    """
    Price an entire option chain (both CE and PE) at once.

    Returns list of dicts with strike, call/put prices, and greeks.
    """
    chain = []
    for K in strikes:
        ce = price_option(spot, K, T, r, sigma, OptionType.CALL)
        pe = price_option(spot, K, T, r, sigma, OptionType.PUT)
        chain.append({
            "strike": K,
            "ce_price": ce.theoretical_price,
            "ce_delta": ce.greeks.delta,
            "ce_gamma": ce.greeks.gamma,
            "ce_theta": ce.greeks.theta,
            "ce_vega": ce.greeks.vega,
            "ce_iv": ce.iv,
            "ce_moneyness": ce.moneyness,
            "pe_price": pe.theoretical_price,
            "pe_delta": pe.greeks.delta,
            "pe_gamma": pe.greeks.gamma,
            "pe_theta": pe.greeks.theta,
            "pe_vega": pe.greeks.vega,
            "pe_iv": pe.iv,
            "pe_moneyness": pe.moneyness,
        })
    return chain


# =============================================================================
# Demo / Self-test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Antigravity Options Greeks Calculator")
    print("=" * 60)

    # NIFTY example
    spot = 25450.0
    strike = 25500.0
    T = 7 / 365         # 7 days to expiry
    r = 0.065            # RBI repo rate ~6.5%
    sigma = 0.14         # 14% IV

    print(f"\nSpot: {spot} | Strike: {strike} | DTE: 7 | IV: {sigma*100}%")
    print("-" * 60)

    # Price CE
    ce = price_option(spot, strike, T, r, sigma, OptionType.CALL)
    print(f"\nCALL {strike}:")
    print(f"  Price     : Rs.{ce.theoretical_price}")
    print(f"  Intrinsic : Rs.{ce.intrinsic_value}")
    print(f"  Time Value: Rs.{ce.time_value}")
    print(f"  Moneyness : {ce.moneyness}")
    print(f"  Delta     : {ce.greeks.delta}")
    print(f"  Gamma     : {ce.greeks.gamma}")
    print(f"  Theta/day : {ce.greeks.theta}")
    print(f"  Vega/1%   : {ce.greeks.vega}")

    # Price PE
    pe = price_option(spot, strike, T, r, sigma, OptionType.PUT)
    print(f"\nPUT {strike}:")
    print(f"  Price     : Rs.{pe.theoretical_price}")
    print(f"  Delta     : {pe.greeks.delta}")
    print(f"  Theta/day : {pe.greeks.theta}")

    # Implied volatility
    print(f"\n--- Implied Volatility ---")
    market_price = 180.0
    iv = implied_volatility(market_price, spot, strike, T, r, OptionType.CALL)
    print(f"  Market price Rs.{market_price} => IV = {iv*100 if iv else 'N/A'}%")

    # Iron Condor payoff
    print(f"\n--- Iron Condor Payoff ---")
    ic = build_iron_condor(
        spot=spot,
        sell_ce_strike=25600, buy_ce_strike=25700,
        sell_pe_strike=25300, buy_pe_strike=25200,
        sell_ce_premium=45, buy_ce_premium=18,
        sell_pe_premium=42, buy_pe_premium=15,
    )
    print(f"  Strategy: {ic.name}")
    print(f"  Net Premium: Rs.{ic.net_premium}")
    print(f"  Max Profit : Rs.{ic.max_profit}")
    print(f"  Max Loss   : Rs.{ic.max_loss}")
    print(f"  Breakevens : {ic.breakeven_points}")

    # Option chain
    print(f"\n--- Quick Chain (5 strikes) ---")
    strikes = get_strikes_around_atm(spot, 4)
    chain = price_chain(spot, strikes, T, sigma, r)
    print(f"{'Strike':>8} | {'CE Price':>8} {'CE D':>6} {'CE Th':>6} | {'PE Price':>8} {'PE D':>6} {'PE Th':>6}")
    for row in chain:
        print(f"{row['strike']:>8.0f} | {row['ce_price']:>8.2f} {row['ce_delta']:>6.3f} {row['ce_theta']:>6.2f} | {row['pe_price']:>8.2f} {row['pe_delta']:>6.3f} {row['pe_theta']:>6.2f}")

    print("\n[OK] Options calculator ready!")
