from app.core.math_utils import round_distance_km, round_expected_loss


def test_round_expected_loss_half_up():
    """Verify that expected_loss implements strict mathematical half-up rounding.
    e.g. 2.5 -> 3, 3.5 -> 4, 1.2 -> 1, 1.8 -> 2.
    """
    # 0.5 * 5 = 2.5 -> Must round up to 3 with ROUND_HALF_UP (whereas banker's round would round to 2)
    assert round_expected_loss(0.5, 5) == 3

    # 0.5 * 7 = 3.5 -> Must round up to 4
    assert round_expected_loss(0.5, 7) == 4

    # 0.25 * 10 = 2.5 -> Must round up to 3
    assert round_expected_loss(0.25, 10) == 3

    # 0.2 * 10 = 2.0 -> Exactly 2
    assert round_expected_loss(0.2, 10) == 2

    # 0.12 * 10 = 1.2 -> Rounds down to 1
    assert round_expected_loss(0.12, 10) == 1


def test_round_distance_km():
    """Verify distance rounding policy."""
    assert round_distance_km(0.0) == 0
    # Between 0 and 0.5 km enforces minimum 1 km for non-zero trips
    assert round_distance_km(0.3) == 1
    assert round_distance_km(0.5) == 1
    assert round_distance_km(1.4) == 1
    assert round_distance_km(1.5) == 2
    assert round_distance_km(12.7) == 13
