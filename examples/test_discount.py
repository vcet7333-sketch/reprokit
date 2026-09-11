from pricing import discounted_price


def test_percentage_discount():
    # A 20% discount on 200 must be 160, not 180.
    assert discounted_price(200, 20) == 160
