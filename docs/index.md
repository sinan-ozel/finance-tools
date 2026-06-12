# finance-tools

An MCP server exposing financial calculation tools. Runs via Docker; connects to any MCP client that supports HTTP transport (Claude Desktop, Claude.ai, Cursor, etc.).

## Quickstart

```bash
docker run -p 8000:8000 sinan-ozel/finance-tools:latest
```

MCP endpoint: `http://localhost:8000/mcp`

All rates — inputs and outputs alike — are expressed in **percent** (e.g. `12` means 12%). Rate inputs are **effective annual rates**, matching the `effective_annual_rate` outputs, so results can be fed from one tool into another.

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
  "monthly_rate": 1.567504,
  "effective_annual_rate": 20.5195,
  "APR": 18.81
}
```

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
→ monthly_rate:          1.567504 %
→ effective_annual_rate: 20.5195 %
→ APR:                   18.81 %
```

---

### `monthly_payment`

The inverse of `annualized_interest_rate`: given a principal, an effective annual rate, and a term in months, returns the fixed monthly payment plus the total amount paid and total interest over the life of the loan.

**Inputs**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `P` | float | yes | — | Principal (original loan balance) |
| `annual_rate` | float | yes | — | Effective annual interest rate in percent |
| `t` | int | no | `9` | Number of monthly payments |

**Output**

```json
{
  "monthly_payment": 885.62,
  "total_paid": 10627.45,
  "total_interest": 627.45
}
```

**How it works**

The effective annual rate is converted to a monthly rate \(r = (1 + R)^{1/12} - 1\), then plugged into the annuity formula:

\[
M = P \cdot \frac{r(1+r)^t}{(1+r)^t - 1}
\]

At a rate of zero the payment degenerates to \(P / t\).

**Example**

A \$10,000 loan at 12% effective annual over 12 months:

```
P = 10000, annual_rate = 12, t = 12
→ monthly_payment: $885.62
→ total_paid:      $10,627.45
→ total_interest:  $627.45
```

---

### `loan_payoff_months`

Computes how long a balance takes to retire at a fixed monthly payment, plus the total paid and total interest. If the payment does not even cover the monthly interest, an error is returned along with the minimum viable payment.

**Inputs**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `P` | float | yes | — | Current loan balance |
| `annual_rate` | float | yes | — | Effective annual interest rate in percent |
| `M` | float | yes | — | Fixed monthly payment amount |

**Output**

```json
{
  "months": 23,
  "years": 1.92,
  "total_paid": 11141.63,
  "total_interest": 1141.63
}
```

When `M` is at or below the monthly interest (here \$100/month against \$10,000 at 24%):

```json
{
  "error": "Payment does not cover monthly interest of 180.88; the balance will never decrease.",
  "minimum_viable_payment": 180.88
}
```

**How it works**

Solving the annuity equation for the term gives:

\[
n = -\frac{\ln\!\left(1 - \dfrac{rP}{M}\right)}{\ln(1+r)}
\]

where \(r\) is the monthly rate. The month count is rounded up (the final payment is smaller), while `total_paid` uses the exact fractional term. At a rate of zero the term degenerates to \(P / M\).

**Example**

A \$10,000 balance at 12% effective annual, paying \$500/month:

```
P = 10000, annual_rate = 12, M = 500
→ months:         23  (1.92 years)
→ total_paid:     $11,141.63
→ total_interest: $1,141.63
```

---

### `future_value`

Projects the growth of an investment: a starting principal compounding at an effective annual rate, with an optional fixed contribution at the end of each month. Separates the final value into what was contributed and what was earned.

**Inputs**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `principal` | float | no | `0` | Starting amount already invested |
| `monthly_contribution` | float | no | `0` | Amount added at the end of each month |
| `annual_rate` | float | yes | — | Effective annual rate of return in percent |
| `months` | int | yes | — | Number of months to project |

**Output**

```json
{
  "future_value": 53881.86,
  "total_contributed": 34000.0,
  "interest_earned": 19881.86
}
```

**How it works**

With monthly rate \(r = (1 + R)^{1/12} - 1\) over \(n\) months:

\[
FV = P(1+r)^n + C \cdot \frac{(1+r)^n - 1}{r}
\]

where \(P\) is the principal and \(C\) the end-of-month contribution. At a rate of zero this degenerates to \(P + Cn\).

**Example**

\$10,000 invested at 7% effective annual, adding \$200/month for 10 years:

```
principal = 10000, monthly_contribution = 200, annual_rate = 7, months = 120
→ future_value:      $53,881.86
→ total_contributed: $34,000.00
→ interest_earned:   $19,881.86
```

---

### `internal_rate_of_return`

Computes the IRR of a series of cash flows at regular intervals: the periodic discount rate at which the net present value is zero, annualized at a configurable frequency. The series must contain at least one outflow (negative) and one inflow (positive).

**Inputs**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `cash_flows` | list[float] | yes | — | Cash flows starting at period 0; outflows negative, inflows positive |
| `periods_per_year` | int | no | `12` | Periods per year used to annualize (12 = monthly, 1 = annual) |

**Output**

```json
{
  "periodic_rate": 7.713847,
  "annualized_rate": 143.9262
}
```

**How it works**

Finds the root of the NPV equation:

\[
\sum_{i=0}^{N} \frac{CF_i}{(1+y)^i} = 0
\]

via Brent's method over the bracket \((-99.99\%,\ 1000\%)\) per period, then annualizes: \((1+y)^{\text{periods per year}} - 1\). An error is returned when the cash flows are all the same sign or when no root exists in the bracket.

**Example**

Invest \$1,000, receive \$300 at the end of each of the next 4 months:

```
cash_flows = [-1000, 300, 300, 300, 300], periods_per_year = 12
→ periodic_rate:   7.713847 %  (per month)
→ annualized_rate: 143.9262 %
```

---

### `bond_yield_to_maturity`

Solves for the yield to maturity of a fixed-coupon bond from its market price, face value, coupon rate, and time to maturity. Supports any compounding frequency; zero-coupon bonds work via `coupon_rate = 0`.

**Inputs**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `price` | float | yes | — | Current market price of the bond |
| `face_value` | float | no | `100` | Face (par) value repaid at maturity |
| `coupon_rate` | float | yes | — | Annual coupon rate in percent of face value |
| `years_to_maturity` | float | yes | — | Years until the bond matures |
| `frequency` | int | no | `2` | Coupon payments per year (2 = semiannual, 1 = annual, 4 = quarterly, 12 = monthly) |

**Output**

```json
{
  "ytm": 5.6617,
  "effective_annual_yield": 5.7418,
  "current_yield": 5.2632,
  "periodic_rate": 2.830845
}
```

- `ytm` — nominal annual yield (periodic rate × frequency), the market quoting convention
- `effective_annual_yield` — compounding-adjusted; comparable with the effective rates from the loan tools
- `current_yield` — annual coupon divided by price
- `periodic_rate` — the raw per-period rate

**How it works**

Finds the periodic yield \(y\) at which the present value of the cash flows equals the price:

\[
\text{price} = \sum_{i=1}^{n} \frac{C}{(1+y)^i} + \frac{F}{(1+y)^n}
\]

where \(C\) is the coupon per period, \(F\) the face value, and \(n\) the number of remaining periods, via Brent's method. Errors are returned for non-positive prices or face values, terms with no remaining payment periods, and prices outside the solvable yield range.

**Example**

A 10-year, 5% semiannual coupon bond trading at 95 (par 100):

```
price = 95, face_value = 100, coupon_rate = 5, years_to_maturity = 10, frequency = 2
→ ytm:                    5.6617 %
→ effective_annual_yield: 5.7418 %
→ current_yield:          5.2632 %
```

---

## Keeping examples honest

Every example on this page is pinned by [`tests/test_doc_examples.py`](https://github.com/sinan-ozel/finance-tools/blob/main/tests/test_doc_examples.py) — if a tool's behavior changes, the test suite fails until the documentation is updated to match.
