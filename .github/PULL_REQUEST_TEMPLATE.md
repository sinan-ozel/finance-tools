## What does this PR do?


## Pre-PR checklist

All of these run through Docker Compose — no local Python needed.

### Required

- [ ] **Tests pass** — `docker compose -f tests/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from test`
- [ ] **Lint passes** — `docker compose -f lint/docker-compose.yaml up --build --abort-on-container-exit`
- [ ] **Code is reformatted** — `docker compose -f reformat/docker-compose.yaml up --build --abort-on-container-exit`
      (CI will commit formatting fixes back to your branch, but running it locally avoids an extra CI round trip)
- [ ] **Docs build cleanly** — `docker compose -f docs-validate/docker-compose.yaml up --build --abort-on-container-exit`

### If you added or changed a tool

- [ ] Input model uses Pydantic `Field` with a description and the `"not": {"type": "null"}` constraint on every field
- [ ] New tests added in `tests/test_*.py` (closed-form checks, edge cases, error paths)
- [ ] Tool documented in `docs/index.md` — input table, sample output, formula, worked example
- [ ] Documented examples pinned in `tests/test_doc_examples.py` (the suite fails if docs and code drift apart)
- [ ] Rate conventions kept consistent: percent in/out, effective annual rates for rate inputs
- [ ] Manually exercised via the Inspector (optional) — `docker compose -f inspector/docker-compose.yaml up --build`, then open the URL from the logs

### Release

- [ ] `__version__` in `server/__init__.py` bumped **if** this should cut a stable release on merge
      (unchanged version → dev tag only; bumped version → `x.y.z` + `latest` on Docker Hub)

If any required item is unchecked, explain why:
