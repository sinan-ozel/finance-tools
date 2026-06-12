"""Pin the exact examples shown in docs/index.md.

If one of these fails, a tool's behavior changed and the documentation needs
updating too.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_doc_example_annualized_interest_rate(mcp_tools):
    result = await mcp_tools(
        "annualized_interest_rate", input={"P": 1000, "M": 120, "t": 9}
    )
    assert result == {
        "monthly_rate": 1.567504,
        "effective_annual_rate": 20.5195,
        "APR": 18.81,
    }


async def test_doc_example_monthly_payment(mcp_tools):
    result = await mcp_tools(
        "monthly_payment", input={"P": 10000, "annual_rate": 12, "t": 12}
    )
    assert result == {
        "monthly_payment": 885.62,
        "total_paid": 10627.45,
        "total_interest": 627.45,
    }


async def test_doc_example_loan_payoff_months(mcp_tools):
    result = await mcp_tools(
        "loan_payoff_months", input={"P": 10000, "annual_rate": 12, "M": 500}
    )
    assert result == {
        "months": 23,
        "years": 1.92,
        "total_paid": 11141.63,
        "total_interest": 1141.63,
    }


async def test_doc_example_loan_payoff_error(mcp_tools):
    result = await mcp_tools(
        "loan_payoff_months", input={"P": 10000, "annual_rate": 24, "M": 100}
    )
    assert result == {
        "error": (
            "Payment does not cover monthly interest of 180.88; "
            "the balance will never decrease."
        ),
        "minimum_viable_payment": 180.88,
    }


async def test_doc_example_future_value(mcp_tools):
    result = await mcp_tools(
        "future_value",
        input={
            "principal": 10000,
            "monthly_contribution": 200,
            "annual_rate": 7,
            "months": 120,
        },
    )
    assert result == {
        "future_value": 53881.86,
        "total_contributed": 34000.0,
        "interest_earned": 19881.86,
    }


async def test_doc_example_internal_rate_of_return(mcp_tools):
    result = await mcp_tools(
        "internal_rate_of_return",
        input={
            "cash_flows": [-1000, 300, 300, 300, 300],
            "periods_per_year": 12,
        },
    )
    assert result == {
        "periodic_rate": 7.713847,
        "annualized_rate": 143.9262,
    }


async def test_doc_example_bond_yield_to_maturity(mcp_tools):
    result = await mcp_tools(
        "bond_yield_to_maturity",
        input={
            "price": 95,
            "face_value": 100,
            "coupon_rate": 5,
            "years_to_maturity": 10,
            "frequency": 2,
        },
    )
    assert result == {
        "ytm": 5.6617,
        "effective_annual_yield": 5.7418,
        "current_yield": 5.2632,
        "periodic_rate": 2.830845,
    }
