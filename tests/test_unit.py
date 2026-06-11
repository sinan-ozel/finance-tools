import pytest

pytestmark = pytest.mark.anyio


def _monthly_payment(P: float, R_annual: float, t: int) -> float:
    """Compute the exact monthly payment for a given principal and annual
    rate."""
    r = (1 + R_annual) ** (1 / 12) - 1
    return P * (r * (1 + r) ** t) / ((1 + r) ** t - 1)


async def test_basic_roundtrip(mcp_tools):
    """Given known M from closed form, recover the annualized rate."""
    P, R_annual, t = 10000, 0.12, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M, "t": t}
    )
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_high_interest(mcp_tools):
    """Loan sharks exist.

    So should tests for them.
    """
    P, R_annual, t = 5000, 0.60, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M, "t": t}
    )
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_low_interest(mcp_tools):
    """For the optimists."""
    P, R_annual, t = 20000, 0.03, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M, "t": t}
    )
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_near_zero_interest(mcp_tools):
    """Practically zero interest.

    Mathematically degenerate.
    """
    P, R_annual, t = 10000, 0.0001, 9
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M, "t": t}
    )
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


async def test_output_keys(mcp_tools):
    """Make sure the dict isn't missing anything."""
    result = await mcp_tools(
        "annualized_interest_rate", input={"P": 10000, "M": 1200, "t": 9}
    )
    assert "monthly_rate" in result
    assert "effective_annual_rate" in result
    assert "APR" in result


async def test_apr_vs_effective(mcp_tools):
    """APR should always be less than effective annual rate (compounding is
    cruel)."""
    result = await mcp_tools(
        "annualized_interest_rate", input={"P": 10000, "M": 1200, "t": 9}
    )
    assert result["APR"] < result["effective_annual_rate"]


async def test_higher_payment_means_higher_rate(mcp_tools):
    """More payment = more interest. Economics 101.

    M must exceed P/t (≈1111 here) — otherwise repayment in t months is
    impossible even at 0% interest.
    """
    P, t = 10000, 9
    result_low = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": 1150, "t": t}
    )
    result_high = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": 1350, "t": t}
    )
    assert (
        result_high["effective_annual_rate"]
        > result_low["effective_annual_rate"]
    )


async def test_default_t(mcp_tools):
    """T defaults to 9 months."""
    P, R_annual, t = 10000, 0.12, 9
    M = _monthly_payment(P, R_annual, t)

    result_explicit = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M, "t": 9}
    )
    result_default = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M}
    )
    assert (
        result_explicit["effective_annual_rate"]
        == result_default["effective_annual_rate"]
    )


async def test_variable_term(mcp_tools):
    """Works for non-default term lengths."""
    P, R_annual, t = 3721.40, 0.20, 16
    M = _monthly_payment(P, R_annual, t)

    result = await mcp_tools(
        "annualized_interest_rate", input={"P": P, "M": M, "t": t}
    )
    assert abs(result["effective_annual_rate"] - R_annual * 100) < 1e-4


# --- monthly_payment ---------------------------------------------------------


async def test_monthly_payment_matches_closed_form(mcp_tools):
    """Payment should match the standard amortization formula."""
    P, annual_rate, t = 250000, 6.0, 360
    r = annual_rate / 100 / 12
    expected = P * (r * (1 + r) ** t) / ((1 + r) ** t - 1)

    result = await mcp_tools(
        "monthly_payment",
        input={"P": P, "annual_rate": annual_rate, "t": t},
    )
    assert abs(result["monthly_payment"] - round(expected, 2)) < 0.01


async def test_monthly_payment_zero_interest(mcp_tools):
    """At 0% the payment is just principal divided by term."""
    result = await mcp_tools(
        "monthly_payment", input={"P": 1200, "annual_rate": 0.0, "t": 12}
    )
    assert abs(result["monthly_payment"] - 100.0) < 1e-6
    assert abs(result["total_interest"]) < 1e-6


async def test_monthly_payment_inverts_rate_tool(mcp_tools):
    """monthly_payment and annualized_interest_rate should round-trip."""
    P, annual_rate, t = 10000, 12.0, 9
    pay = await mcp_tools(
        "monthly_payment",
        input={"P": P, "annual_rate": annual_rate, "t": t},
    )
    back = await mcp_tools(
        "annualized_interest_rate",
        input={"P": P, "M": pay["monthly_payment"], "t": t},
    )
    assert abs(back["APR"] - annual_rate) < 0.05


# --- future_value ------------------------------------------------------------


async def test_future_value_lump_sum(mcp_tools):
    """A lump sum compounds without contributions."""
    result = await mcp_tools(
        "future_value",
        input={
            "present_value": 1000,
            "annual_rate": 12,
            "years": 1,
            "periods_per_year": 12,
        },
    )
    assert abs(result["future_value"] - 1000 * (1.01) ** 12) < 0.01


async def test_future_value_zero_rate_contributions(mcp_tools):
    """At 0% rate, future value is just principal plus contributions."""
    result = await mcp_tools(
        "future_value",
        input={
            "present_value": 500,
            "annual_rate": 0,
            "years": 2,
            "periods_per_year": 12,
            "contribution": 100,
        },
    )
    assert abs(result["future_value"] - (500 + 100 * 24)) < 1e-6
    assert abs(result["interest_earned"]) < 1e-6


# --- present_value -----------------------------------------------------------


async def test_present_value_inverts_future_value(mcp_tools):
    """Discounting a compounded lump sum recovers the original principal."""
    fv = await mcp_tools(
        "future_value",
        input={
            "present_value": 1000,
            "annual_rate": 7,
            "years": 10,
            "periods_per_year": 12,
        },
    )
    pv = await mcp_tools(
        "present_value",
        input={
            "future_value": fv["future_value"],
            "annual_rate": 7,
            "years": 10,
            "periods_per_year": 12,
        },
    )
    assert abs(pv["present_value"] - 1000) < 0.01


# --- compound_annual_growth_rate ---------------------------------------------


async def test_cagr_doubling(mcp_tools):
    """Doubling over 1 year is a 100% CAGR."""
    result = await mcp_tools(
        "compound_annual_growth_rate",
        input={"begin_value": 100, "end_value": 200, "years": 1},
    )
    assert abs(result["CAGR"] - 100.0) < 1e-4
    assert abs(result["total_return"] - 100.0) < 1e-4


async def test_cagr_known_value(mcp_tools):
    """100 -> 200 over 10 years is a well-known ~7.18% CAGR."""
    result = await mcp_tools(
        "compound_annual_growth_rate",
        input={"begin_value": 100, "end_value": 200, "years": 10},
    )
    assert abs(result["CAGR"] - 7.1773) < 1e-2


# --- net_present_value -------------------------------------------------------


async def test_npv_zero_rate_is_sum(mcp_tools):
    """At 0% discount, NPV is just the sum of cash flows."""
    result = await mcp_tools(
        "net_present_value",
        input={"cash_flows": [-100, 50, 50, 50], "annual_rate": 0},
    )
    assert abs(result["net_present_value"] - 50) < 1e-6


async def test_npv_discounts_future(mcp_tools):
    """A positive future flow is worth less than face at a positive rate."""
    result = await mcp_tools(
        "net_present_value",
        input={"cash_flows": [0, 110], "annual_rate": 10},
    )
    assert abs(result["net_present_value"] - 100) < 1e-6


# --- internal_rate_of_return -------------------------------------------------


async def test_irr_makes_npv_zero(mcp_tools):
    """The IRR fed back into NPV should yield approximately zero."""
    cash_flows = [-1000, 300, 400, 500, 600]
    irr = await mcp_tools(
        "internal_rate_of_return", input={"cash_flows": cash_flows}
    )
    check = await mcp_tools(
        "net_present_value",
        input={
            "cash_flows": cash_flows,
            "annual_rate": irr["IRR_per_period"],
        },
    )
    assert abs(check["net_present_value"]) < 1.0


async def test_irr_known_value(mcp_tools):
    """-100 today, 110 next period is exactly a 10% IRR."""
    result = await mcp_tools(
        "internal_rate_of_return", input={"cash_flows": [-100, 110]}
    )
    assert abs(result["IRR_per_period"] - 10.0) < 1e-4
