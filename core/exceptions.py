"""
Antigravity Trading — Custom Exceptions
Hierarchical exception system for clean error handling.
"""


class AntGravityError(Exception):
    """Base exception for all Antigravity Trading errors."""
    pass


# ---------------------------------------------------------------------------
# Config errors
# ---------------------------------------------------------------------------

class ConfigError(AntGravityError):
    """Configuration loading or validation error."""
    pass


class MissingConfigError(ConfigError):
    """Required configuration value is missing."""
    pass


# ---------------------------------------------------------------------------
# Broker errors
# ---------------------------------------------------------------------------

class BrokerError(AntGravityError):
    """Base broker error."""
    def __init__(self, broker: str, message: str):
        self.broker = broker
        super().__init__(f"[{broker}] {message}")


class BrokerConnectionError(BrokerError):
    """Failed to connect to broker API."""
    pass


class BrokerAuthError(BrokerError):
    """Authentication failed."""
    pass


class BrokerOrderError(BrokerError):
    """Order placement / modification / cancellation failed."""
    def __init__(self, broker: str, message: str, order_id: str = ""):
        self.order_id = order_id
        super().__init__(broker, f"Order {order_id}: {message}" if order_id else message)


class BrokerDataError(BrokerError):
    """Historical data fetch error."""
    pass


# ---------------------------------------------------------------------------
# Data errors
# ---------------------------------------------------------------------------

class DataError(AntGravityError):
    """Data layer error."""
    pass


class InstrumentNotFoundError(DataError):
    """Requested instrument not found in master."""
    def __init__(self, symbol: str, exchange: str = ""):
        self.symbol = symbol
        self.exchange = exchange
        super().__init__(f"Instrument not found: {symbol}" + (f" on {exchange}" if exchange else ""))


class DataNotAvailableError(DataError):
    """Historical data not available for requested range."""
    pass


class DataIntegrityError(DataError):
    """Data corruption or inconsistency detected."""
    pass


# ---------------------------------------------------------------------------
# Strategy errors
# ---------------------------------------------------------------------------

class StrategyError(AntGravityError):
    """Strategy execution error."""
    def __init__(self, strategy_id: str, message: str):
        self.strategy_id = strategy_id
        super().__init__(f"[Strategy:{strategy_id}] {message}")


class StrategyInitError(StrategyError):
    """Strategy failed to initialize."""
    pass


class StrategyRuntimeError(StrategyError):
    """Strategy raised an error during execution."""
    pass


# ---------------------------------------------------------------------------
# Risk errors
# ---------------------------------------------------------------------------

class RiskViolation(AntGravityError):
    """Risk limit breached — order blocked."""
    def __init__(self, rule: str, message: str):
        self.rule = rule
        super().__init__(f"Risk violation [{rule}]: {message}")


class MaxLossBreached(RiskViolation):
    """Maximum loss limit exceeded."""
    pass


class PositionLimitBreached(RiskViolation):
    """Maximum position count or value exceeded."""
    pass


class CircuitBreakerTriggered(RiskViolation):
    """Portfolio drawdown exceeded circuit breaker threshold."""
    pass
