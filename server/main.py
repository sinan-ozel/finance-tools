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


class NPVInput(BaseModel):
    """Input for the net_present_value tool."""

    discount_rate: float = Field(
        description="Annual discount rate as a decimal (e.g. 0.10 for 10%).",
        json_schema_extra={"not": {"type": "null"}},
    )
    cash_flows: List[float] = Field(
        description=(
            "Ordered list of cash flows starting at period 0 "
            "(the initial outlay, usually negative), followed by inflows."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def net_present_value(input: NPVInput) -> dict:
    """Compute the Net Present Value of a series of periodic cash flows.

    Discounts each cash flow in the list back to period 0 at the given annual
    rate and sums them.  A positive NPV means the investment adds value at
    that discount rate; negative means it destroys value.
    """
    r = input.discount_rate
    npv = sum(cf / (1 + r) ** t for t, cf in enumerate(input.cash_flows))
    return {"npv": round(npv, 4)}


class IRRInput(BaseModel):
    """Input for the internal_rate_of_return tool."""

    cash_flows: List[float] = Field(
        description=(
            "Ordered list of cash flows starting at period 0 "
            "(initial outlay, usually negative).  Must contain at least one "
            "sign change so an IRR exists."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def internal_rate_of_return(input: IRRInput) -> dict:
    """Find the Internal Rate of Return (IRR) for a series of cash flows.

    The IRR is the annual discount rate that makes the NPV of the cash flows
    equal to zero.  Useful for comparing the profitability of investments
    without specifying an external discount rate.
    """
    cfs = input.cash_flows

    def npv_at_r(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in enumerate(cfs))

    try:
        irr = brentq(npv_at_r, -0.9999, 100.0)
    except ValueError as exc:
        raise ValueError(
            "No IRR found in [-99.99%, 10000%]. "
            "Ensure cash flows contain at least one sign change."
        ) from exc

    return {"irr": round(irr * 100, 4)}


class BondYTMInput(BaseModel):
    """Input for the bond_yield_to_maturity tool."""

    face_value: float = Field(
        description="Face (par) value of the bond.",
        json_schema_extra={"not": {"type": "null"}},
    )
    coupon_rate: float = Field(
        description="Annual coupon rate as a decimal (e.g. 0.05 for 5%).",
        json_schema_extra={"not": {"type": "null"}},
    )
    price: float = Field(
        description="Current market price of the bond.",
        json_schema_extra={"not": {"type": "null"}},
    )
    years_to_maturity: float = Field(
        description="Number of years until the bond matures.",
        json_schema_extra={"not": {"type": "null"}},
    )
    periods_per_year: int = Field(
        default=2,
        description=(
            "Coupon payment frequency per year: 2 = semiannual (default), "
            "1 = annual, 4 = quarterly."
        ),
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def bond_yield_to_maturity(input: BondYTMInput) -> dict:
    """Solve for the Yield to Maturity (YTM) of a fixed-coupon bond.

    Given the bond's face value, coupon rate, current market price, and time
    to maturity, returns the annualised YTM and the simpler current yield so
    you can compare the bond against other fixed-income instruments.
    """
    n = round(input.years_to_maturity * input.periods_per_year)
    coupon = input.face_value * input.coupon_rate / input.periods_per_year

    def price_at_y(y: float) -> float:
        y_per = y / input.periods_per_year
        if abs(y_per) < 1e-10:
            return coupon * n + input.face_value - input.price
        pv_coupons = coupon * (1 - (1 + y_per) ** (-n)) / y_per
        pv_face = input.face_value / (1 + y_per) ** n
        return pv_coupons + pv_face - input.price

    ytm = brentq(price_at_y, 1e-10, 100.0)
    current_yield = (input.face_value * input.coupon_rate) / input.price

    return {
        "yield_to_maturity": round(ytm * 100, 4),
        "current_yield": round(current_yield * 100, 4),
    }


class FutureValueInput(BaseModel):
    """Input for the future_value tool."""

    principal: float = Field(
        description="Initial lump-sum investment.",
        json_schema_extra={"not": {"type": "null"}},
    )
    monthly_contribution: float = Field(
        default=0.0,
        description="Additional amount contributed at the end of each month.",
        json_schema_extra={"not": {"type": "null"}},
    )
    annual_rate: float = Field(
        description="Expected annual growth/interest rate as a decimal.",
        json_schema_extra={"not": {"type": "null"}},
    )
    years: float = Field(
        description="Investment horizon in years.",
        json_schema_extra={"not": {"type": "null"}},
    )


@mcp.tool()
def future_value(input: FutureValueInput) -> dict:
    """Project the future value of an investment with optional monthly contributions.

    Compounds the principal monthly and adds an ordinary annuity for regular
    contributions.  Returns the total future value alongside a breakdown of
    how much was contributed vs. how much came from growth — useful for
    retirement planning, savings goals, and comparing investment strategies.
    """
    r = input.annual_rate / 12
    n = round(input.years * 12)

    fv_principal = input.principal * (1 + r) ** n
    if abs(r) < 1e-10:
        fv_contributions = input.monthly_contribution * n
    else:
        fv_contributions = input.monthly_contribution * ((1 + r) ** n - 1) / r

    total = fv_principal + fv_contributions
    total_contributed = input.principal + input.monthly_contribution * n

    return {
        "future_value": round(total, 2),
        "total_contributed": round(total_contributed, 2),
        "total_interest_earned": round(total - total_contributed, 2),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
