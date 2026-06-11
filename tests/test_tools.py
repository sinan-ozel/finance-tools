import pytest

pytestmark = pytest.mark.anyio


def _monthly_payment(P: float, R_annual: float, t: int) -> float:
    """Compute the exact monthly payment for a given principal and annual
    rate."""
    r = (1 + R_annual) ** (1 / 12) - 1
    return P * (r * (1 + r) ** t) / ((1 + r) ** t - 1)


async def test_monthly_payment_matches_closed_form(mcp_tools):
    """The tool should agree with the textbook annuity formula."""
    P, R_annual, t = 10000, 0.12, 9
    expected = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "monthly_payment", input={"P": P, "annual_rate": 12, "t": t}
    )
    assert abs(result["monthly_payment"] - expected) < 0.01


async def test_monthly_payment_roundtrip(mcp_tools):
    """Feeding the payment back into annualized_interest_rate should recover
    the original rate."""
    P, t = 10000, 12
    payment = await mcp_tools(
        "monthly_payment", input={"P": P, "annual_rate": 18, "t": t}
    )
    rate = await mcp_tools(
        "annualized_interest_rate",
        input={"P": P, "M": payment["monthly_payment"], "t": t},
    )
    assert abs(rate["effective_annual_rate"] - 18) < 0.01


async def test_monthly_payment_zero_rate(mcp_tools):
    """At 0% the payment is just principal divided by term."""
    result = await mcp_tools(
        "monthly_payment", input={"P": 1200, "annual_rate": 0, "t": 12}
    )
    assert abs(result["monthly_payment"] - 100) < 0.01
    assert abs(result["total_interest"]) < 0.01


async def test_monthly_payment_totals_are_consistent(mcp_tools):
    """Total paid = payment x term, total interest = total paid -
    principal."""
    P, t = 5000, 24
    result = await mcp_tools(
        "monthly_payment", input={"P": P, "annual_rate": 10, "t": t}
    )
    assert abs(result["total_paid"] - result["monthly_payment"] * t) < 0.01 * t
    assert abs(result["total_interest"] - (result["total_paid"] - P)) < 0.01


async def test_payoff_recovers_term(mcp_tools):
    """Paying the exact amortizing payment should pay off in exactly the
    original term."""
    P, R_annual, t = 10000, 0.12, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "loan_payoff_months", input={"P": P, "annual_rate": 12, "M": M}
    )
    assert result["months"] == t


async def test_payoff_zero_rate(mcp_tools):
    """At 0% the payoff time is just balance divided by payment."""
    result = await mcp_tools(
        "loan_payoff_months", input={"P": 1200, "annual_rate": 0, "M": 100}
    )
    assert result["months"] == 12
    assert abs(result["total_interest"]) < 0.01


async def test_payoff_impossible_payment(mcp_tools):
    """A payment below the monthly interest never retires the loan."""
    result = await mcp_tools(
        "loan_payoff_months", input={"P": 10000, "annual_rate": 24, "M": 100}
    )
    assert "error" in result
    assert result["minimum_viable_payment"] > 100


async def test_payoff_bigger_payment_is_faster(mcp_tools):
    """Paying more each month shortens the loan."""
    result_low = await mcp_tools(
        "loan_payoff_months", input={"P": 10000, "annual_rate": 12, "M": 300}
    )
    result_high = await mcp_tools(
        "loan_payoff_months", input={"P": 10000, "annual_rate": 12, "M": 600}
    )
    assert result_high["months"] < result_low["months"]


async def test_future_value_zero_rate(mcp_tools):
    """At 0% the future value is just what was put in."""
    result = await mcp_tools(
        "future_value",
        input={
            "principal": 1000,
            "monthly_contribution": 100,
            "annual_rate": 0,
            "months": 12,
        },
    )
    assert abs(result["future_value"] - 2200) < 0.01
    assert abs(result["interest_earned"]) < 0.01


async def test_future_value_lump_sum(mcp_tools):
    """With no contributions, growth follows compound interest exactly."""
    result = await mcp_tools(
        "future_value",
        input={"principal": 10000, "annual_rate": 7, "months": 120},
    )
    assert abs(result["future_value"] - 10000 * 1.07**10) < 0.01


async def test_future_value_contributions_beat_lump_alone(mcp_tools):
    """Adding contributions must end above the lump-sum-only result."""
    base = await mcp_tools(
        "future_value",
        input={"principal": 5000, "annual_rate": 5, "months": 60},
    )
    with_savings = await mcp_tools(
        "future_value",
        input={
            "principal": 5000,
            "monthly_contribution": 200,
            "annual_rate": 5,
            "months": 60,
        },
    )
    assert with_savings["future_value"] > base["future_value"] + 200 * 60


async def test_irr_recovers_loan_rate(mcp_tools):
    """The IRR of a loan's cash flows is the loan's monthly rate."""
    P, R_annual, t = 10000, 0.12, 9
    M = _monthly_payment(P, R_annual, t)
    flows = [-P] + [M] * t

    result = await mcp_tools(
        "internal_rate_of_return",
        input={"cash_flows": flows, "periods_per_year": 12},
    )
    assert abs(result["annualized_rate"] - 12) < 1e-3


async def test_irr_annual_periods(mcp_tools):
    """With annual periods, periodic and annualized rates coincide."""
    flows = [-1000, 0, 0, 1331]  # 10% per year over 3 years

    result = await mcp_tools(
        "internal_rate_of_return",
        input={"cash_flows": flows, "periods_per_year": 1},
    )
    assert abs(result["periodic_rate"] - 10) < 1e-3
    assert abs(result["annualized_rate"] - 10) < 1e-3


async def test_irr_requires_mixed_signs(mcp_tools):
    """All-positive cash flows have no IRR."""
    result = await mcp_tools(
        "internal_rate_of_return", input={"cash_flows": [100, 200, 300]}
    )
    assert "error" in result
