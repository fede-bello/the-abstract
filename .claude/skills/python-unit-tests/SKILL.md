---
name: python-unit-tests
description: Best-practice rules for writing pytest tests in the-abstract backend (backend/tests/) — naming, structure, fixtures, mocking at the clients/ boundary, assertion quality, parametrize, the unit-vs-LLM-integration split, and what NOT to test. Load before writing, refactoring, or reviewing any test_*.py, or whenever the user mentions tests, pytest, fixtures, mocks, or coverage.
---

# Python Unit Tests

Test code is still code — the function-shape, helper-placement, mutation, and exception rules in `python-code-quality` all apply here. This skill covers the test-specific concerns on top of those: what makes a *good* test, where to draw the line between unit and integration, and the pytest patterns this repo expects.

The goal of a test is to fail loudly when the production code is wrong and pass quietly when it isn't. Anything else (style, "best practice" rituals, AAA labels) is overhead.

## What counts as a unit test here

- Lives under `backend/tests/`, mirroring the source layout (`backend/src/arxiv_digest/steps/classification/step.py` → `backend/tests/steps/classification/test_step.py`; a client → `backend/tests/clients/test_arxiv.py`).
- Filename: `test_*.py` (`testpaths = ["backend/tests"]`). Tests import from `arxiv_digest....` directly — `pythonpath = ["backend/src"]` is set, so no `sys.path` hacks.
- Class grouping: `class TestXxx:` with no `__init__`, no `setUp`. Class-level state belongs in a `scope="class"` fixture.
- Function: `def test_*` or `async def test_*`. Anything without the prefix is silently ignored.
- A unit test runs in well under a second, opens no sockets, calls **no real LLM and no real arXiv**, and touches no real Postgres. If it needs a live backend, it's an integration test (below).

## Unit vs integration

The one registered marker is `integration: tests that call a real LLM backend`. The split in this repo is **unit = mock the `clients/` boundary; integration = hit a real backend**.

- Integration tests carry `@pytest.mark.integration` and **guard on availability**, skipping cleanly when no backend/credentials are present — so `uv run pytest` stays green for anyone who clones the repo. `test_classification.py` is the canonical example: it `pytest.skip(...)`s when `backend_available()` is False, then asserts an accuracy floor over a curated fixture.
- Run fast tests with `uv run pytest -m "not integration"`; run the live ones with `uv run pytest -m integration`.
- Anything reaching arXiv or downloading PDFs is also integration — mock `clients.arxiv.fetch_recent_papers` in unit tests.

## F.I.R.S.T. — the parts that actually matter

- **Fast.** Most tests in under a second so the suite stays usable on every save. (LLM/arXiv calls are why those tests are quarantined behind `integration`.)
- **Independent.** No test relies on another's side effects or execution order. If you can't reorder your file's tests at random and still pass, there's hidden state.
- **Repeatable.** Same result on your machine, in CI, and in a clean container. Usual culprits: local timezone, the wall clock, unseeded randomness, the filesystem, and an unmocked network/LLM call.
- **Self-validating.** Pass/fail is binary. Never assert by reading stdout or eyeballing a log line.
- **Timely.** Written alongside the production code. Tests written weeks later usually expose a design that's hard to test — that's a signal, not an inconvenience.

## Naming and structure

- Name tests as descriptive sentences: `test_returns_empty_when_no_papers`, not `test_empty`. The function name is the failure message.
- Don't write `# Arrange / # Act / # Assert` markers. A blank line between phases and a clear name carry the same information without noise.
- One concept per test. `test_classify_and_filter_and_order` is three tests — split them so a failure points at one thing.
- A test should fail for exactly one reason.
- Group related tests in `class TestX:` when they share fixtures or read better together. Don't group just to group — top-level functions are fine.

## Assertions

- Prefer asserting on whole objects: `assert result == ClassificationResult(label="useful", rationale=...)`. Pytest's diff tells you exactly which field differs; five sequential `assert result.x == ...` lines lose that.
- Pydantic models and dataclasses get a useful `__repr__` for free — it pays off every time a test fails.
- Use `pytest.raises(LLMError, match=r"no JSON object")` to verify the message, not just the type. A bare `pytest.raises(LLMError)` passes for *any* `LLMError`, including one from an unrelated earlier bug.
- `pytest.approx` for float equality. Never `round(x, 5) == round(y, 5)`.
- Don't assert tautologies. `assert result is not None` after a function whose signature returns `ClassificationResult` tests nothing — that's `python-code-quality`'s "don't re-check the known" applied to tests.
- `assert sorted(actual) == sorted(expected)` (or `set(...)`) when order is incidental. Classification fan-in is order-deterministic via `collect_events`, so order *is* part of the contract there — assert it.

## Test data and time

- Build small factories (`make_paper(**overrides)`) with neutral defaults instead of 12-field inline `Paper(...)` blocks. `test_classification.py`'s `_to_paper` is exactly this pattern — promote it to a shared builder when a second test needs a `Paper`.
- Values in assertions should be derived from or named after their meaning, not bare magic numbers (tests are exempt from the `PLR2004` lint, so this is discipline, not a linter).
- Freeze time at the boundary when behavior depends on "now" — `clients/arxiv.py`'s `_build_query` uses `datetime.now(UTC)`, so any test of it must control the clock. Add `freezegun` or `time-machine` to the `dev` extras rather than monkeypatching `datetime` in several places.
- Test in UTC explicitly. Tests that pass on your laptop and fail in CI's timezone are a classic time-sink.
- Seed any randomness (`random.seed(0)`) so failures reproduce — `clients/arxiv.py`'s backoff jitter is a live source of nondeterminism.

## Test size — coverage without scaffold bloat

A test under five lines of *real* setup is easy to read; under twenty is still fine. The moment you build a 12-field `Paper` inline four times, or paste a full arXiv payload that fills the screen, the test has crossed into scaffold bloat — and the fields that *don't* affect the assertion are now louder than the ones that do.

**Coverage doesn't have to suffer.** A function with a happy path, two edge cases, and a boundary still gets four tests. Test *count* is fine; what shrinks is the *scaffolding inside each test*.

The compression recipe, in order:

1. **Build a factory** (`make_paper(**overrides)`) with neutral defaults that don't trigger any branch. Put it in a normal module (`backend/tests/_builders.py`), not in `conftest.py`, so it imports normally.
2. **Each test names only the fields that drive its assertion.** If the assertion checks the useful/noise filter, the inputs are the labels — the other `Paper` fields stay on defaults.
3. **Whole-object equality on the output** when it's a model — one diff line beats five field asserts.
4. **One concept per test, but the *concept* is a row in the behaviour table.** "keeps useful", "drops noise", "empty input → empty output", boundary value — four small tests, each ~10 lines.

A test is too long when, on reading it, you can't tell within ten seconds *which input* drives *which assertion*. That's a scaffold-bloat smell, not a "the behaviour is complicated" smell.

What this does *not* mean: don't merge separate concepts to shrink line count; don't skip edge cases (boundaries are cheap with a factory); and **don't hide the assertion's driving input behind a factory default** — if a test cares that `label="noise"` drops a paper, it must pass that explicitly, not rely on the default happening to produce the asserted outcome.

**Symptom to watch for**: a test that sets a field the production code never reads has grown its own folklore. Refactoring with a factory exposes it — the test then sets only what the code actually consumes.

## Mocking — what to mock and where

- **Mock at *your* `clients/` boundary, not third-party internals.** Mock `clients.llm.complete_structured` or `clients.arxiv.fetch_recent_papers`, not `litellm.acompletion`, `claude_agent_sdk.query`, or `arxiv.Client.results`. The closer to the third party you go, the more your test couples to its implementation — swapping LiteLLM for another backend shouldn't break a classification-logic test.
- **Patch where the name is looked up, not where it's defined.** The classifier does `from arxiv_digest.clients.llm import complete_structured`, so patch `arxiv_digest.steps.classification.step.complete_structured`, not the client module.
- **Prefer fakes over mocks** when feasible. A small async stub that returns a canned `ClassificationResult` is more honest than a `MagicMock` with hand-wired returns, and survives refactors.
- **Always pass `spec=`** when you do use `Mock` / `MagicMock`. Without it, `m.typo_method()` silently returns another Mock and your test passes while production blows up.
- **Don't assert call counts unless the count is the point.** `assert_called_once_with(...)` is right when "exactly once" is the contract (idempotency, no-duplicate-LLM-call); it's noise when you only care the call happened with the right args.
- **`monkeypatch` vs `unittest.mock.patch`:** `monkeypatch` is lightest for env vars and module attributes (auto-restores). `patch` fits when you need a `MagicMock` with call assertions. Pick per case; neither is the default.
- **Running a whole workflow in a test:** instantiate `DigestWorkflow(timeout=...)`, monkeypatch the step entry points (`fetch_papers`, `classify_paper`) on the `workflows.digest` module namespace, and assert on the `StopEvent` result — that's how the classification fan-out is exercised end-to-end without a network.

## Fixtures

- `yield` over `return` whenever the fixture owns a resource (a `tmp_path` PDF dir, a patched setting). Cleanup after the `yield` runs even if the test crashes — `return` skips it on failure.
- Broader-scoped fixtures cannot depend on narrower-scoped ones — a `scope="session"` fixture depending on a `function`-scoped one is a `ScopeMismatch`, by design.
- **Fixture factories**: when a fixture must be customizable per test, return an inner function:

  ```python
  @pytest.fixture
  def make_paper():
      def _make(**overrides):
          return Paper(arxiv_id="1", entry_id="e", title="t", abstract="a",
                       authors=[], primary_category="cs.LG", categories=["cs.LG"],
                       published=_FIXED_DT, updated=_FIXED_DT, pdf_url="u", **overrides)
      return _make
  ```

- **`autouse=True`** only for non-intrusive, cross-cutting setup: seeding random, blocking outbound network. Anything that affects the *logic* under test should be an explicit fixture parameter — `autouse` hides where state comes from.
- Name fixtures as the thing they provide (`make_paper`, `tmp_pdf_dir`), not as verbs (`setup_paper`).
- **Overriding `settings`**: prefer `monkeypatch.setattr(settings, "llm_max_concurrency", 1)` over re-instantiating `Settings`, and restore via the fixture. Don't reach into `os.environ` after import — `config.py` is read once at import.

## conftest.py

- Use nested `conftest.py` files once shared fixtures appear — a root `backend/tests/conftest.py` for cross-cutting setup, folder-level conftests (e.g. `backend/tests/steps/conftest.py`) for area-specific fixtures. Don't pile everything into one file. (None exist yet — add them when a fixture is genuinely shared, not preemptively.)
- **Never `from conftest import …`.** `conftest.py` is pytest's implicit plugin space — importing from it bypasses discovery and breaks when it moves. Helper functions and factories belong in a normal module (`backend/tests/_builders.py`) and are imported normally.

## Parametrize over loops

- `@pytest.mark.parametrize` over `for case in cases: assert ...`. Each case is reported separately — when one fails you see exactly which input broke.
- Use `pytest.param(..., id="...")` for readable IDs. Without it you get `test_foo[None-True-3]` in failure output.
- Don't parametrize conceptually different cases (different error paths, different setup). Two separate tests beat one parametrized test with `if expected_error:` branches inside.

## Pytest features worth using

- `caplog` to assert on log records (the SDK-fallback warning, the arXiv backoff log), `capsys` for stdout/stderr — beats mocking the logger.
- `tmp_path` for filesystem work (PDF download dirs) — auto-cleaned, no `tempfile` boilerplate.
- `--lf` (last-failed) / `--ff` (failed-first) for tight iteration after a failure.
- `-k "substring"` to run a subset by name; `pytest --collect-only` when discovery feels broken.

## Anti-patterns to recognise

- **Snapshot tests freeze the current output.** Fine for stable structured artifacts (a rendered digest HTML, a JSON shape contract); dangerous as a general strategy because "regenerate the snapshot" silently accepts whatever the code now produces.
- **Don't test framework code.** Pydantic already tests its validation; the `workflows` library tests its event routing. A test asserting Pydantic rejects a missing field tests Pydantic, not you.
- **Don't test private helpers directly.** A test on `_format_metadata` is a sign it either wants to be public (move and test it there) or should be tested through `classify_paper`.
- **Don't auto-retry flaky tests.** Auto-retry hides real bugs — flakiness is almost always a race, a timezone, unseeded randomness, or a real backend call that slipped into a unit test. Quarantine and fix.
- **Watch for tests that always pass.** If commenting out the production logic doesn't break the test, the test isn't testing anything. Gut-check a new test: break the code, confirm it fails, revert.
- **Avoid placeholder asserts** like `assert True` or `assert result`. A `pytest.skip("not implemented")` is more honest.

## Coverage

- Use coverage to *find* untested branches, not as a target number. 100% line coverage with weak assertions is worse than 80% with strong ones.
- Branch coverage > line coverage. "Both sides of the `if` ran" is what you actually care about.
- `# pragma: no cover` for genuinely unreachable code — a defensive `else: raise`, the SDK-fallback path when no SDK is installed, `if __name__ == "__main__"`.

## This repo's conventions (read before writing)

- `pyproject.toml` sets `asyncio_mode = "auto"`, so `async def test_…` works without `@pytest.mark.asyncio`. Don't add the marker.
- `pythonpath = ["backend/src"]` is set — import production code as `from arxiv_digest... import ...`. No path manipulation in tests.
- The `integration` marker is registered for tests that call a real LLM backend; gate them on `backend_available()` and skip cleanly. Keep `uv run pytest -m "not integration"` green with zero credentials.
- mypy `exclude`s `backend/tests/`, and ruff `per-file-ignores` for `backend/tests/**` drops `S101` (assert), `D` (docstrings), `ANN` (annotations), `PLR2004` (magic values), and `INP001` (no `__init__`). So tests need no docstrings or type hints and may use literal expected values freely — but ruff `select = ["ALL"]` still governs everything else; tests are not a style free-for-all.
- Read a neighbouring test (`backend/tests/test_classification.py`) before writing a new one — match the fixture/skip/assert patterns already in place.
