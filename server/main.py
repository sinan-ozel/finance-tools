import logging

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

    Given a principal P repaid in t equal monthly payments of M, returns
    the implied monthly rate, effective annual rate, and APR — so the cost
    of the loan can be compared against other instruments like credit cards
    or mortgages.
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
