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


# ---------------------------------------------------------------------------
# net_present_value
# ---------------------------------------------------------------------------


async def test_npv_known_value(mcp_tools):
    """NPV of a simple investment with a known closed-form answer."""
    # -1000 today, +600 in year 1, +600 in year 2 at 10% discount
    # NPV = -1000 + 600/1.1 + 600/1.21 = 40.0661...
    result = await mcp_tools(
        "net_present_value",
        input={"discount_rate": 0.10, "cash_flows": [-1000, 600, 600]},
    )
    assert abs(result["npv"] - 40.0661) < 0.01


async def test_npv_zero_at_irr(mcp_tools):
    """NPV is (approximately) zero when discounted at the IRR."""
    irr_result = await mcp_tools(
        "internal_rate_of_return",
        input={"cash_flows": [-1000, 300, 400, 500]},
    )
    r = irr_result["irr"] / 100
    npv_result = await mcp_tools(
        "net_present_value",
        input={"discount_rate": r, "cash_flows": [-1000, 300, 400, 500]},
    )
    assert abs(npv_result["npv"]) < 1e-2


async def test_npv_positive_for_profitable_project(mcp_tools):
    """A clearly profitable project has positive NPV."""
    result = await mcp_tools(
        "net_present_value",
        input={"discount_rate": 0.05, "cash_flows": [-100, 60, 60, 60]},
    )
    assert result["npv"] > 0


async def test_npv_negative_for_bad_project(mcp_tools):
    """A project that barely pays back at all has negative NPV."""
    result = await mcp_tools(
        "net_present_value",
        input={"discount_rate": 0.20, "cash_flows": [-1000, 100, 100, 100]},
    )
    assert result["npv"] < 0


# ---------------------------------------------------------------------------
# internal_rate_of_return
# ---------------------------------------------------------------------------


async def test_irr_known_value(mcp_tools):
    """IRR of a textbook example matches expected value."""
    # -100, +110 in year 1 → IRR = 10%
    result = await mcp_tools(
        "internal_rate_of_return",
        input={"cash_flows": [-100, 110]},
    )
    assert abs(result["irr"] - 10.0) < 1e-4


async def test_irr_multiperiod(mcp_tools):
    """Multi-period IRR round-trips through NPV."""
    cfs = [-500, 100, 200, 300]
    irr_result = await mcp_tools(
        "internal_rate_of_return", input={"cash_flows": cfs}
    )
    r = irr_result["irr"] / 100
    npv_result = await mcp_tools(
        "net_present_value",
        input={"discount_rate": r, "cash_flows": cfs},
    )
    assert abs(npv_result["npv"]) < 1e-2


async def test_irr_higher_return_beats_lower(mcp_tools):
    """A more profitable project has a higher IRR."""
    result_low = await mcp_tools(
        "internal_rate_of_return",
        input={"cash_flows": [-1000, 1050]},
    )
    result_high = await mcp_tools(
        "internal_rate_of_return",
        input={"cash_flows": [-1000, 1200]},
    )
    assert result_high["irr"] > result_low["irr"]


# ---------------------------------------------------------------------------
# bond_yield_to_maturity
# ---------------------------------------------------------------------------


async def test_ytm_par_bond(mcp_tools):
    """A bond priced at par has YTM equal to its coupon rate."""
    result = await mcp_tools(
        "bond_yield_to_maturity",
        input={
            "face_value": 1000,
            "coupon_rate": 0.06,
            "price": 1000,
            "years_to_maturity": 10,
            "periods_per_year": 2,
        },
    )
    assert abs(result["yield_to_maturity"] - 6.0) < 1e-3


async def test_ytm_discount_bond(mcp_tools):
    """A bond trading below par has YTM above its coupon rate."""
    result = await mcp_tools(
        "bond_yield_to_maturity",
        input={
            "face_value": 1000,
            "coupon_rate": 0.05,
            "price": 950,
            "years_to_maturity": 5,
            "periods_per_year": 2,
        },
    )
    assert result["yield_to_maturity"] > 5.0


async def test_ytm_premium_bond(mcp_tools):
    """A bond trading above par has YTM below its coupon rate."""
    result = await mcp_tools(
        "bond_yield_to_maturity",
        input={
            "face_value": 1000,
            "coupon_rate": 0.08,
            "price": 1050,
            "years_to_maturity": 5,
            "periods_per_year": 2,
        },
    )
    assert result["yield_to_maturity"] < 8.0


async def test_ytm_output_keys(mcp_tools):
    """Response includes both yield_to_maturity and current_yield."""
    result = await mcp_tools(
        "bond_yield_to_maturity",
        input={
            "face_value": 1000,
            "coupon_rate": 0.05,
            "price": 980,
            "years_to_maturity": 3,
        },
    )
    assert "yield_to_maturity" in result
    assert "current_yield" in result


# ---------------------------------------------------------------------------
# future_value
# ---------------------------------------------------------------------------


async def test_fv_lump_sum_known(mcp_tools):
    """Lump-sum FV: $1000 at 12% annual for 1 year (monthly compounding)."""
    # (1 + 0.01)^12 ≈ 1.126825
    result = await mcp_tools(
        "future_value",
        input={
            "principal": 1000,
            "monthly_contribution": 0,
            "annual_rate": 0.12,
            "years": 1,
        },
    )
    assert abs(result["future_value"] - 1126.83) < 0.01


async def test_fv_contributions_add_up(mcp_tools):
    """Regular contributions increase future value beyond principal-only
    growth."""
    result_no_contrib = await mcp_tools(
        "future_value",
        input={
            "principal": 10000,
            "monthly_contribution": 0,
            "annual_rate": 0.07,
            "years": 10,
        },
    )
    result_with_contrib = await mcp_tools(
        "future_value",
        input={
            "principal": 10000,
            "monthly_contribution": 200,
            "annual_rate": 0.07,
            "years": 10,
        },
    )
    assert result_with_contrib["future_value"] > result_no_contrib["future_value"]


async def test_fv_zero_rate(mcp_tools):
    """At 0% interest, future value equals total contributions."""
    result = await mcp_tools(
        "future_value",
        input={
            "principal": 1000,
            "monthly_contribution": 100,
            "annual_rate": 0.0,
            "years": 5,
        },
    )
    expected = 1000 + 100 * 60
    assert abs(result["future_value"] - expected) < 0.01
    assert abs(result["total_interest_earned"]) < 0.01


async def test_fv_output_keys(mcp_tools):
    """Response includes all three expected keys."""
    result = await mcp_tools(
        "future_value",
        input={"principal": 5000, "annual_rate": 0.05, "years": 3},
    )
    assert "future_value" in result
    assert "total_contributed" in result
    assert "total_interest_earned" in result


async def test_fv_interest_earned_positive_at_positive_rate(mcp_tools):
    """Interest earned is strictly positive when rate > 0."""
    result = await mcp_tools(
        "future_value",
        input={
            "principal": 5000,
            "monthly_contribution": 100,
            "annual_rate": 0.06,
            "years": 5,
        },
    )
    assert result["total_interest_earned"] > 0
