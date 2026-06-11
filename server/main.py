import logging
import math

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
        description=(
            "Effective annual interest rate in percent, e.g. 12 for 12%."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )
    t: int = Field(
        default=9,
        description="Number of monthly payments.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def monthly_payment(input: MonthlyPaymentInput) -> dict:
    """Compute the fixed monthly payment for a loan.

    The inverse of annualized_interest_rate: given a principal P, an
    effective annual rate, and a term of t months, returns the monthly
    payment plus the total amount paid and total interest over the life of
    the loan.
    """
    r = (1 + input.annual_rate / 100) ** (1 / 12) - 1
    if abs(r) < 1e-10:
        M = input.P / input.t
    else:
        M = input.P * (r * (1 + r) ** input.t) / ((1 + r) ** input.t - 1)
    total_paid = M * input.t

    return {
        "monthly_payment": round(M, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_paid - input.P, 2),
    }


class LoanPayoffInput(BaseModel):
    """Input for the loan_payoff_months tool."""

    P: float = Field(
        description="Current loan balance.",
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description=(
            "Effective annual interest rate in percent, e.g. 12 for 12%."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )
    M: float = Field(
        description="Fixed monthly payment amount.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def loan_payoff_months(input: LoanPayoffInput) -> dict:
    """Compute how long it takes to pay off a loan at a fixed payment.

    Given a balance P, an effective annual rate, and a monthly payment M,
    returns the number of months until the balance reaches zero, plus the total
    paid and total interest. If the payment does not even cover the monthly
    interest, the loan can never be repaid and an error is returned instead.
    """
    r = (1 + input.annual_rate / 100) ** (1 / 12) - 1
    if abs(r) < 1e-10:
        n = input.P / input.M
    else:
        monthly_interest = r * input.P
        if input.M <= monthly_interest:
            return {
                "error": (
                    "Payment does not cover monthly interest of "
                    f"{round(monthly_interest, 2)}; "
                    "the balance will never decrease."
                ),
                "minimum_viable_payment": round(monthly_interest, 2),
            }
        n = -math.log(1 - r * input.P / input.M) / math.log(1 + r)

    months = math.ceil(n - 1e-9)
    total_paid = input.M * n

    return {
        "months": months,
        "years": round(months / 12, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_paid - input.P, 2),
    }


class FutureValueInput(BaseModel):
    """Input for the future_value tool."""

    principal: float = Field(
        default=0.0,
        description="Starting amount already invested.",
        json_schema_extra={"not": {"type": "null"}},
    )
    monthly_contribution: float = Field(
        default=0.0,
        description=(
            "Amount added at the end of each month. May be zero for a "
            "lump-sum projection."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description=(
            "Effective annual rate of return in percent, e.g. 7 for 7%."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )
    months: int = Field(
        description="Number of months to project.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def future_value(input: FutureValueInput) -> dict:
    """Project the future value of an investment.

    Grows a starting principal at the given effective annual rate, with an
    optional fixed contribution at the end of each month. Returns the final
    value alongside the total contributed and the interest earned, so growth
    from saving can be separated from growth from returns.
    """
    r = (1 + input.annual_rate / 100) ** (1 / 12) - 1
    n = input.months
    growth = (1 + r) ** n
    if abs(r) < 1e-10:
        fv = input.principal + input.monthly_contribution * n
    else:
        fv = input.principal * growth + input.monthly_contribution * (
            (growth - 1) / r
        )
    total_contributed = input.principal + input.monthly_contribution * n

    return {
        "future_value": round(fv, 2),
        "total_contributed": round(total_contributed, 2),
        "interest_earned": round(fv - total_contributed, 2),
    }


class IRRInput(BaseModel):
    """Input for the internal_rate_of_return tool."""

    cash_flows: list[float] = Field(
        description=(
            "Cash flows at regular intervals, starting at period 0. "
            "Outflows (investments) are negative, inflows are positive, "
            "e.g. [-1000, 300, 300, 300, 300]."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )
    periods_per_year: int = Field(
        default=12,
        description=(
            "Number of cash-flow periods per year, used to annualize the "
            "periodic rate. Use 12 for monthly flows, 1 for annual."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def internal_rate_of_return(input: IRRInput) -> dict:
    """Compute the internal rate of return of a series of cash flows.

    Finds the periodic discount rate at which the net present value of the cash
    flows is zero, then annualizes it. The series must contain at least one
    negative and one positive cash flow.
    """
    flows = input.cash_flows
    if not any(cf < 0 for cf in flows) or not any(cf > 0 for cf in flows):
        return {
            "error": (
                "Cash flows must include at least one outflow (negative) "
                "and one inflow (positive)."
            )
        }

    def npv(r: float) -> float:
        return sum(cf / (1 + r) ** i for i, cf in enumerate(flows))

    lo, hi = -0.9999, 10.0
    if npv(lo) * npv(hi) > 0:
        return {
            "error": (
                "No internal rate of return found between -99.99% and "
                "1000% per period."
            )
        }

    r = brentq(npv, lo, hi)
    annualized = (1 + r) ** input.periods_per_year - 1

    return {
        "periodic_rate": round(r * 100, 6),
        "annualized_rate": round(annualized * 100, 4),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
