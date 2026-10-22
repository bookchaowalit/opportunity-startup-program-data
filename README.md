# book-startup-program-data

Compare startup admission, stage requirements, equity and perks.

Status: **local source pilot**, version 0.1.0. Five manually invoked official
sources now use the shared local lake runtime; there is no published remote,
scheduler, hosted API, or consumer integration. The CLI provides a
machine-readable JSON contract, validates explicit exports, and searches
synthetic examples. It never falls back from live data to fixtures.

## Users and boundary

For people and small teams discovering startup programs.
Cohort or founder membership packages; standalone grants and general coupons have other owners.

Subcategories: accelerator, incubator, venture-builder, founder-residency, startup-perks.

Domain-specific terms: `startup_stage`, `equity_required`, `cohort_start`, `incorporation_required`.
Each record represents one program/offer intake window. A repeat intake receives
a distinct source record ID. Cross-domain packages use `related_records` rather
than copying the same award into several products.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
book-startup-program-data contract
book-startup-program-data demo --open-only
book-startup-program-data demo --query "accelerator"
book-startup-program-data validate src/book_startup_program_data/demo.json
python -m unittest discover -s tests -v
```

Developer checks (the same commands CI runs in `.github/workflows/ci.yml` on
Python 3.10 and 3.12, plus a `contract`/`validate`/`demo` CLI smoke):

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
```

All tests are offline: source adapters are exercised with inline fixtures, the
capture entry point is only checked for its fail-closed guard, and no test needs
the shared data-lake runtime or network access. `tests/test_policy.py` keeps
`sources.json`, every `source*.json` policy and the bundled schema consistent.

With dependencies already available, use `PYTHONPATH=src python3 -m book_startup_program_data`.
`demo` uses the fixed synthetic clock 2026-09-07T00:00:00Z unless `--as-of` is
provided. `--open-only` excludes closed, unknown-deadline, expired, stale (72h
default), and future-checked records. This is an availability filter; it does
not assert personal eligibility, selection probability, or a guaranteed payout.

Contract: `src/book_startup_program_data/schema.json` (`startup_program.v1`).
Unknown amounts, currencies, eligibility and deadlines remain unknown. Cash,
credit, discount, in-kind benefits and access are different value kinds. Never
sum them as cash income. Queries and validation are read-only and do not persist
provided files. The `live` label requires captured lineage, but validation alone
does not verify that referenced lake objects exist or prove source truth.

## Data ownership and source policy

Owner: bookchaowalit. Public program metadata only; no applications, personal
screening answers, financial credentials, cookies, or private transcripts.
See `sources.json` and `src/book_startup_program_data/source-google-startups-accelerator-us.json`.
The Google for Startups United States page is reviewed for public read access
and captured only for bounded program metadata. The page states equity-free
support, technical participation and product-credit benefits, but does not
publish a current intake deadline. Re-check the current program before applying.
No spending, account creation, applications or messaging is performed by this
adapter.

Implemented flow: approved source pull → immutable landing bytes
and checksum → Bronze Parquet and manifest through the shared lake runtime →
versioned read-only contract → consumer pull. Each product owns its source
adapters and lake prefix. Producers never write into another app's database,
CRM, tasks, application tracker, or notification system.

## Official source pilots

The five enabled sources are listed in `sources.json` and
`src/book_startup_program_data/source*.json`. They include [Google for Startups Accelerator: United States](https://startup.google.com/programs/accelerator/united-states/), [Google Startup School](https://startup.google.com/programs/startup-school/), [Entrepreneurs First](https://www.joinef.com/), [Antler](https://www.antler.co/pitch), and [AWS Activate](https://aws.amazon.com/startups/credits/).
The page describes a ten-week hybrid accelerator for US-based technology
startups, ideally Seed to Series A, with equity-free support, mentoring,
technical help, AI early access and product-credit benefits. Availability and
the current intake deadline remain unknown because the captured page does not
publish a current application window. Unknown domain terms remain null rather
than being inferred.

Run with the existing data-lake Python environment:

```bash
export SOLO_DATA_LAKE_ROOT=/path/to/solo-data-lake
PYTHONPATH=src "$SOLO_DATA_LAKE_ROOT/.venv/bin/python" -m book_startup_program_data.capture acquire --lake "$PWD/data/lake" --state-dir "$PWD/data/control"
PYTHONPATH=src "$SOLO_DATA_LAKE_ROOT/.venv/bin/python" -m book_startup_program_data.capture records --lake "$PWD/data/lake" --state-dir "$PWD/data/control"
```

The lane depends on the explicit local `discovery.capture_runtime` v1. Capture
is manual, rate-limited to one check per six hours, and rejects sensitive source
markers before archival. A failed latest fetch has no fixture fallback; parser
failures leave a quarantined capture reference.

## Next implementation gates

1. Keep the five source adapters fresh and add parser fixtures when a provider changes its public contract.
2. Add live source tests, retention/access controls and runtime monitoring.
3. Connect a read-only consumer. Personal eligibility, ranking, deadlines and
   application workflow belong to consumers with separate private storage.

No runtime port is reserved. The former `opportunity.v1` is archival; `job.v1` remains a separate job-data contract.
Breaking contract changes require a new version and a consumer migration.
There is no production deployment to roll back; discard demo output or restore
the previous contract version locally. Source permission, live availability,
lake replay and real eligibility are **unverified**, not passing gates.

## Development

```bash
uv sync --frozen --all-extras && uv run mypy  # locked env (uv.lock) as CI installs it
uv run pytest -q --cov
```
