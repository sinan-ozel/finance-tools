# finance-tools

An MCP server exposing financial calculation tools. Runs via Docker; connects to any MCP client that supports HTTP transport (Claude Desktop, Claude.ai, Cursor, etc.).

## Quickstart

```bash
docker run -p 8000:8000 sinan-ozel/finance-tools:latest
```

MCP endpoint: `http://localhost:8000/mcp`

---

## Tools

### `annualized_interest_rate`

Solves for the implied interest rate of a fixed-payment loan given the principal, monthly payment, and number of payments. Returns the monthly rate, effective annual rate (EAR), and APR so the cost can be compared against other instruments such as credit cards or mortgages.

**Inputs**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `P` | float | yes | — | Principal (original loan balance) |
| `M` | float | yes | — | Fixed monthly payment amount |
| `t` | int | no | `9` | Number of monthly payments |

**Output**

```json
{
  "monthly_rate": 1.234567,
  "effective_annual_rate": 16.0755,
  "APR": 14.8148
}
```

All rates are in **percent**.

**How it works**

The tool solves for the monthly rate \(r\) in the standard annuity equation:

\[
M = P \cdot \frac{r(1+r)^t}{(1+r)^t - 1}
\]

using Brent's method (via `scipy.optimize.brentq`). From \(r\) it derives:

- **EAR** \(= (1+r)^{12} - 1\)
- **APR** \(= r \times 12\)

**Example**

A \$1,000 loan repaid in 9 monthly payments of \$120:

```
P = 1000, M = 120, t = 9
→ monthly_rate:          1.787400 %
→ effective_annual_rate: 23.5936 %
→ APR:                   21.4488 %
```
