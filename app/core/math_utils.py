from decimal import Decimal, ROUND_HALF_UP


def round_expected_loss(failure_probability: float, travel_cost: int) -> int:
    """Compute expected loss using explicit mathematical half-up rounding (ROUND_HALF_UP).

    Formula: expected_loss = failure_probability * travel_cost

    NOTE: Python's built-in round() uses round-half-to-even (banker's rounding),
    which rounds 2.5 to 2 and 3.5 to 4. To ensure deterministic commercial half-up
    rounding where .5 always rounds up, we use Decimal with ROUND_HALF_UP.
    """
    p_dec = Decimal(str(failure_probability))
    cost_dec = Decimal(str(travel_cost))
    raw_loss = p_dec * cost_dec
    return int(raw_loss.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_distance_km(raw_km: float) -> int:
    """Convert floating-point distance to whole kilometres using explicit half-up rounding.

    Distances strictly between 0 and 0.5 km round to 1 km if positive travel is required,
    otherwise standard half-up quantization applies.
    """
    if raw_km <= 0.0:
        return 0
    dec_km = Decimal(str(raw_km))
    rounded = int(dec_km.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(1, rounded)
