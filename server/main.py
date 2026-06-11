import logging
from typing import List

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from scipy.optimize import brentq

mcp = FastMCP("finance-tools")


class _SuppressMCPUnionValidation(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.getMessage().startswith("Failed to validate request:")


logging.getLogger().addFilter(_SuppressMCPUnionValidation())


class AnnualizedRateInput(BaseModel):
    """Input for the annualized_interest_rate tool."""

    P: float = Field(
        description="Principal amount (the original loan balance).",
        json_schema_extra={"not": {"type": "null"}},
    )
    M: float = Field(
        description="Fixed monthly payment amount.",
        json_schema_extra={"not": {"type": "null"}},
    )
    t: int = Field(
        default=9,
        description="Number of monthly payments.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def annualized_interest_rate(input: AnnualizedRateInput) -> dict:
    """Solve for the annualized interest rate of a fixed-payment loan.

    Given a principal P repaid in t equal monthly payments of M, returns the
    implied monthly rate, effective annual rate, and APR — so the cost of the
    loan can be compared against other instruments like credit cards or
    mortgages.
    """

    def f(r: float) -> float:
        if abs(r) < 1e-10:
            return input.P / input.t - input.M
        return (
            input.P * (r * (1 + r) ** input.t) / ((1 + r) ** input.t - 1)
            - input.M
        )

    r = brentq(f, 1e-10, 10.0)
    effective_annual = (1 + r) ** 12 - 1
    apr = r * 12

    return {
        "monthly_rate": round(r * 100, 6),
        "effective_annual_rate": round(effective_annual * 100, 4),
        "APR": round(apr * 100, 4),
    }


class MonthlyPaymentInput(BaseModel):
    """Input for the monthly_payment tool."""

    P: float = Field(
        description="Principal amount (the original loan balance).",
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description="Nominal annual interest rate as a percent, e.g. 6.5 for 6.5%.",
        json_schema_extra={"not": {"type": "null"}},
    )
    t: int = Field(
        description="Number of monthly payments (loan term in months).",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def monthly_payment(input: MonthlyPaymentInput) -> dict:
    """Compute the fixed monthly payment for an amortizing loan.

    Given a principal P, a nominal annual interest rate, and a term of t
    months, returns the level monthly payment along with the total amount
    repaid and the total interest paid over the life of the loan. This is the
    inverse of ``annualized_interest_rate``.
    """
    r = input.annual_rate / 100 / 12
    if abs(r) < 1e-12:
        payment = input.P / input.t
    else:
        payment = input.P * (r * (1 + r) ** input.t) / ((1 + r) ** input.t - 1)
    total_paid = payment * input.t

    return {
        "monthly_payment": round(payment, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_paid - input.P, 2),
    }


class FutureValueInput(BaseModel):
    """Input for the future_value tool."""

    present_value: float = Field(
        description="Amount invested or owed today.",
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description="Nominal annual interest rate as a percent, e.g. 7 for 7%.",
        json_schema_extra={"not": {"type": "null"}},
    )
    years: float = Field(
        description="Investment horizon in years (may be fractional).",
        json_schema_extra={"not": {"type": "null"}},
    )
    periods_per_year: int = Field(
        default=12,
        description="Compounding (and contribution) periods per year. 12 = monthly.",
        json_schema_extra={"not": {"type": "null"}},
    )
    contribution: float = Field(
        default=0.0,
        description="Recurring contribution added at the end of every period.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def future_value(input: FutureValueInput) -> dict:
    """Project the future value of an investment with optional contributions.

    Compounds ``present_value`` at the given annual rate over ``years``, and
    adds an ordinary annuity of recurring ``contribution`` payments made at the
    end of every period. Returns the future value alongside the total amount
    contributed and the interest earned.
    """
    r = input.annual_rate / 100 / input.periods_per_year
    n = input.periods_per_year * input.years

    fv_principal = input.present_value * (1 + r) ** n
    if abs(r) < 1e-12:
        fv_contrib = input.contribution * n
    else:
        fv_contrib = input.contribution * (((1 + r) ** n - 1) / r)

    fv = fv_principal + fv_contrib
    total_contributed = input.present_value + input.contribution * n

    return {
        "future_value": round(fv, 2),
        "total_contributed": round(total_contributed, 2),
        "interest_earned": round(fv - total_contributed, 2),
    }


class PresentValueInput(BaseModel):
    """Input for the present_value tool."""

    future_value: float = Field(
        description="Amount to be received or paid at the end of the horizon.",
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description="Annual discount rate as a percent, e.g. 5 for 5%.",
        json_schema_extra={"not": {"type": "null"}},
    )
    years: float = Field(
        description="Number of years until the amount is received.",
        json_schema_extra={"not": {"type": "null"}},
    )
    periods_per_year: int = Field(
        default=12,
        description="Compounding periods per year. 12 = monthly.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def present_value(input: PresentValueInput) -> dict:
    """Discount a single future cash flow back to today's dollars.

    Answers "what is a future amount worth now?" by discounting
    ``future_value`` at the given annual rate over ``years``. Returns the
    present value and the total discount applied.
    """
    r = input.annual_rate / 100 / input.periods_per_year
    n = input.periods_per_year * input.years
    pv = input.future_value / (1 + r) ** n

    return {
        "present_value": round(pv, 2),
        "discount": round(input.future_value - pv, 2),
    }


class CAGRInput(BaseModel):
    """Input for the compound_annual_growth_rate tool."""

    begin_value: float = Field(
        description="Value at the start of the period.",
        json_schema_extra={"not": {"type": "null"}},
    )
    end_value: float = Field(
        description="Value at the end of the period.",
        json_schema_extra={"not": {"type": "null"}},
    )
    years: float = Field(
        description="Length of the period in years (must be greater than 0).",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def compound_annual_growth_rate(input: CAGRInput) -> dict:
    """Compute the compound annual growth rate (CAGR) of an investment.

    Returns the smoothed annualized return that would take ``begin_value`` to
    ``end_value`` over ``years``, plus the total (non-annualized) return for
    the whole period.
    """
    cagr = (input.end_value / input.begin_value) ** (1 / input.years) - 1
    total_return = input.end_value / input.begin_value - 1

    return {
        "CAGR": round(cagr * 100, 4),
        "total_return": round(total_return * 100, 4),
    }


class CashFlowInput(BaseModel):
    """Input for the net_present_value tool."""

    cash_flows: List[float] = Field(
        description=(
            "Cash flows by period, starting at period 0 (today). Negative "
            "values are outflows, positive values are inflows."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description="Discount rate per period as a percent, e.g. 8 for 8%.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def net_present_value(input: CashFlowInput) -> dict:
    """Compute the net present value (NPV) of a series of cash flows.

    Discounts each cash flow back to period 0 at the given per-period rate and
    sums them. A positive NPV means the cash-flow stream creates value at that
    discount rate.
    """
    r = input.annual_rate / 100
    npv = sum(cf / (1 + r) ** i for i, cf in enumerate(input.cash_flows))

    return {"net_present_value": round(npv, 2)}


class IRRInput(BaseModel):
    """Input for the internal_rate_of_return tool."""

    cash_flows: List[float] = Field(
        description=(
            "Cash flows by period, starting at period 0 (today). Typically the "
            "first value is a negative outflow followed by positive inflows."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def internal_rate_of_return(input: IRRInput) -> dict:
    """Solve for the internal rate of return (IRR) of a cash-flow stream.

    Finds the per-period discount rate at which the net present value of the
    cash flows equals zero, and reports it as both a per-period rate and an
    annualized rate (assuming monthly periods). Raises if no rate brackets a
    sign change in the feasible range.
    """

    def npv(r: float) -> float:
        return sum(cf / (1 + r) ** i for i, cf in enumerate(input.cash_flows))

    irr = brentq(npv, -0.9999, 10.0)
    annualized = (1 + irr) ** 12 - 1

    return {
        "IRR_per_period": round(irr * 100, 4),
        "annualized_IRR": round(annualized * 100, 4),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
