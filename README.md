![CI/CD](https://github.com/sinan-ozel/finance-tools/actions/workflows/ci.yaml/badge.svg?branch=main)
![Docker Hub](https://img.shields.io/docker/v/sinan-ozel/finance-tools?label=Docker%20Hub)
![License](https://img.shields.io/github/license/sinan-ozel/finance-tools.svg)

# finance-tools

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server exposing financial calculation tools — loan rates and payments, investment projections, IRR, and bond yields. Built with [FastMCP](https://github.com/jlowin/fastmcp), runs via Docker, and connects to any MCP client that supports HTTP transport (Claude Desktop, Claude.ai, Cursor, etc.).

Full documentation: <https://sinan-ozel.github.io/finance-tools/>

## Quickstart

```bash
docker run -p 8000:8000 sinan-ozel/finance-tools:latest
```

The MCP endpoint is at:

```
http://localhost:8000/mcp
```

The server uses **Streamable HTTP** transport (the current MCP standard).

---

## Tools

| Tool | What it does |
|---|---|
| `annualized_interest_rate` | Solves for the implied rate of a fixed-payment loan; returns monthly rate, effective annual rate, and APR |
| `monthly_payment` | The inverse: fixed monthly payment for a principal, rate, and term, plus total paid and total interest |
| `loan_payoff_months` | How long a balance takes to retire at a fixed payment; flags payments that don't cover monthly interest |
| `future_value` | Projects investment growth from a principal and optional monthly contributions, separating contributions from interest earned |
| `internal_rate_of_return` | IRR of a cash-flow series (NPV = 0), with the periodic rate annualized at a configurable frequency |
| `bond_yield_to_maturity` | Solves for YTM and current yield of a fixed-coupon bond; supports any compounding frequency |

All rates are expressed in **percent** (e.g. `12` for 12%). Loan and investment tools use effective annual rates consistently, so outputs from one tool can be fed into another. See the [documentation site](https://sinan-ozel.github.io/finance-tools/) for full input/output schemas and examples.

---

## Development

The only requirement is **Docker** — every dev operation runs through Docker Compose.

### Run the tests

```bash
docker compose -f tests/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from test
```

This starts the MCP server, waits for it to be healthy, then runs pytest against it with `pytest-mcp-tools`.

### Lint

```bash
docker compose -f lint/docker-compose.yaml up --build --abort-on-container-exit
```

### Reformat

```bash
docker compose -f reformat/docker-compose.yaml up --build --abort-on-container-exit
```

Reformatting runs `black`, `docformatter`, and `isort` on `server/` and `tests/`, then writes changes back to disk (via volume mount). On non-main branches CI commits these changes automatically.

### Validate docs

```bash
docker compose -f docs-validate/docker-compose.yaml up --build --abort-on-container-exit
```

### Run the MCP Inspector

```bash
docker compose -f inspector/docker-compose.yaml up --build
```

Then open the URL printed in the logs (includes the auth token):
```
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=<token>
```

---

## VS Code Tasks

Open **Terminal → Run Task** (or `Ctrl+Shift+P → Tasks: Run Task`):

| Task | What it does |
|---|---|
| `test` | Runs the full test suite (server + test runner containers) |
| `lint` | Runs ruff against `server/` and `tests/` |
| `reformat` | Formats code with black + docformatter + isort |
| `validate-docs` | Builds MkDocs site with `--strict` |
| `inspector` | Starts the server + MCP Inspector (leaves running in background) |

---

## CI/CD Pipeline

The workflow at [.github/workflows/ci.yaml](.github/workflows/ci.yaml) runs on every push and pull request:

```
push (any branch)
│
├── reformat        ← runs black/isort/docformatter
│   └── (commits reformatted code back, non-main branches only)
│
├── lint            ← ruff check (needs: reformat)
├── test            ← pytest --mcp-tools (needs: reformat)
├── validate-docs   ← mkdocs build --strict
└── detect-changes  ← checks if server/ or README changed
    │
    └── publish (main only, when changed)
        ├── Build & push Docker image to Docker Hub
        │   ├── stable:  sinan-ozel/finance-tools:1.2.3  +  :latest
        │   └── dev:     sinan-ozel/finance-tools:1.2.4.dev202401011200
        ├── Tag stable release in git
        ├── Create GitHub Release
        └── publish-docs (stable + docs exist)
            └── mike deploy to GitHub Pages
```

### Versioning

Version is read from `server/__init__.py`. The logic:

- If `__version__` > last git tag → **stable release** (tags git, pushes `:latest`)
- If `__version__` == last git tag → **dev release** (appends `.devYYYYMMDDHHMM`, no `:latest`)

Bump `__version__` in `server/__init__.py` to trigger a stable release on the next main push.

---

## Project Structure

```
.
├── Dockerfile                   # Builds and runs the MCP server
├── pyproject.toml               # Project metadata, dependencies, tool config
├── server/
│   ├── __init__.py              # __version__ = "x.y.z"
│   └── main.py                  # FastMCP server — all tools live here
├── tests/
│   ├── Dockerfile               # Test runner image
│   ├── docker-compose.yaml      # mcp-server + test-runner services
│   ├── test_unit.py             # Tests for annualized_interest_rate
│   └── test_tools.py            # Tests for the remaining tools
├── docs/                        # MkDocs documentation site
├── reformat/                    # black + docformatter + isort container
├── lint/                        # ruff container
├── docs-validate/               # mkdocs build container
├── inspector/                   # MCP Inspector + server for visual testing
├── scripts/
│   └── semver_compare.py        # Used by CI to compare versions
└── .github/workflows/ci.yaml    # Full CI/CD pipeline
```

## License

[MIT](LICENSE)
