import pytest

pytestmark = pytest.mark.anyio


def _monthly_payment(P: float, R_annual: float, t: int) -> float:
    """Compute the exact monthly payment for a given principal and annual rate."""
    r = (1 + R_annual) ** (1 / 12) - 1
    return P * (r * (1 + r) ** t) / ((1 + r) ** t - 1)


async def test_basic_roundtrip(mcp_tools):
    """Given known M from closed form, recover the annualized rate."""
    P, R_annual, t = 10000, 0.12, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M, "t": t})
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_high_interest(mcp_tools):
    """Loan sharks exist. So should tests for them."""
    P, R_annual, t = 5000, 0.60, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M, "t": t})
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_low_interest(mcp_tools):
    """For the optimists."""
    P, R_annual, t = 20000, 0.03, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M, "t": t})
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_near_zero_interest(mcp_tools):
    """Practically zero interest. Mathematically degenerate."""
    P, R_annual, t = 10000, 0.0001, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M, "t": t})
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_output_keys(mcp_tools):
    """Make sure the dict isn't missing anything."""
    result = await mcp_tools("annualized_interest_rate", input={"P": 10000, "M": 1200, "t": 9})
    assert "monthly_rate" in result
    assert "effective_annual_rate" in result
    assert "APR" in result


async def test_apr_vs_effective(mcp_tools):
    """APR should always be less than effective annual rate (compounding is cruel)."""
    result = await mcp_tools("annualized_interest_rate", input={"P": 10000, "M": 1200, "t": 9})
    assert result["APR"] < result["effective_annual_rate"]


async def test_higher_payment_means_higher_rate(mcp_tools):
    """More payment = more interest. Economics 101.

    M must exceed P/t (≈1111 here) — otherwise repayment in t months is
    impossible even at 0% interest.
    """
    P, t = 10000, 9
    result_low = await mcp_tools("annualized_interest_rate", input={"P": P, "M": 1150, "t": t})
    result_high = await mcp_tools("annualized_interest_rate", input={"P": P, "M": 1350, "t": t})
    assert result_high["effective_annual_rate"] > result_low["effective_annual_rate"]


async def test_default_t(mcp_tools):
    """t defaults to 9 months."""
    P, R_annual, t = 10000, 0.12, 9
    M = _monthly_payment(P, R_annual, t)

    result_explicit = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M, "t": 9})
    result_default = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M})
    assert result_explicit["effective_annual_rate"] == result_default["effective_annual_rate"]


async def test_variable_term(mcp_tools):
    """Works for non-default term lengths."""
    P, R_annual, t = 3721.40, 0.20, 16
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools("annualized_interest_rate", input={"P": P, "M": M, "t": t})
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4
