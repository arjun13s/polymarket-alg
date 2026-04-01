# Polymarket AI System

This version is scaffolded to be HUD-first at the provider layer while keeping the internal contracts generic enough to swap inference providers later.

## Short Architecture Explanation

This scaffold is organized around a strict pipeline:

1. `market_data` ingests and normalizes Polymarket markets through replaceable adapters.
2. `research` collects source material, extracts claims, and synthesizes pro/con evidence into a typed packet.
3. `agent` orchestrates a transparent workflow: planner, researcher, skeptic, rule check, probability estimate, final memo.
4. `pricing` converts market prices to implied probabilities, estimates fair probability, applies fees/slippage, and blocks weak or uncertain trades.
5. `ranking` compares candidate opportunities across EV, confidence, liquidity, resolution clarity, freshness, and disagreement.
6. `portfolio` sizes positions conservatively and enforces no-trade conditions.
7. `execution` is isolated and starts with paper-only trade placement.
8. `evaluation` is separated so calibration, Brier score, and hit-rate can be measured later without contaminating decision logic.
9. `storage` persists snapshots, research runs, and recommendations via a replaceable database layer.
10. `infra` centralizes configuration, provider routing, logging, and reproducibility primitives, with HUD.ai as the default provider target.

The intended principle is that research, pricing, and execution remain decoupled. You should be able to improve model quality, swap providers, or change storage without rewriting the rest of the system. The composition root is now separated from the workflow so runtime wiring can evolve from `demo` to `paper` to `live` without changing core module code.

## Architecture Diagram

```text
market ingestion -> market snapshot storage -> orchestrator
                                      -> RulesAgent
                                      -> ResearchAgent
                                      -> SkepticAgent
                                      -> ProbabilityAgent
                                      -> deterministic EV / filters
                                      -> decision output
                                      -> ranking / portfolio / execution
                                      -> run + decision persistence
```

## Agent Flow

The current code keeps the orchestration thin and the math deterministic:

1. Fetch or load the market snapshot.
2. Select the outcome being evaluated.
3. Run research collection and synthesis.
4. Run the skeptic pass for the bear case.
5. Estimate fair probability.
6. Compute edge and EV in pure Python.
7. Apply confidence and edge filters.
8. Emit a structured decision and persist the run.

The repository already has the backbone for this flow in `agent/`, `pricing/`, `ranking/`, `portfolio/`, `storage/`, and `app.py`. The next step is to split the workflow into explicit specialist subagents rather than letting one workflow class carry all responsibilities.

## Subagent Responsibilities

- `ResearchAgent`: gather evidence, extract claims, and summarize supporting and opposing facts.
- `RulesAgent`: parse resolution rules, identify ambiguity, and surface interpretation risk.
- `SkepticAgent`: challenge the thesis, look for crowd-efficiency, stale evidence, and missing assumptions.
- `ProbabilityAgent`: synthesize research into a calibrated fair probability estimate.
- `Orchestrator`: delegate to specialists, enforce ordering, and make the final `NO_TRADE`, `WATCHLIST`, or `PAPER_TRADE` decision.

## How To Add A New Subagent

1. Define a typed input model and output model.
2. Keep deterministic math out of the subagent; let it focus on reasoning, extraction, or critique.
3. Register the subagent in the orchestrator as an explicit step.
4. Add a scenario or integration test for its output shape.
5. Add a persistence hook if the new subagent produces durable artifacts.

## HUD Integration

The current code already routes model selection through `src/polymarket_ai/infra/providers.py` and `Settings.provider`. Set `POLYMARKET_AI_PROVIDER=hud` plus HUD credentials to make HUD the default provider path.

The next HUD layer should expose the following tool boundaries as scenario-level wrappers:

- `get_market_data`
- `search_web`
- `fetch_source`
- `parse_rules`
- `compute_ev`
- `save_run`

Those tools should map cleanly onto the same service and repository boundaries used in the Python code, so the HUD environment and the local backend stay aligned.

## Failure Modes

- Ambiguous resolution rules can make a good-looking trade impossible to evaluate correctly.
- Illiquid markets can show apparent edge that disappears after spread and slippage.
- Low-quality research can produce confident but weak probability estimates.
- Over-attention can make the market more efficient than the signal suggests.
- Missing run IDs or stage traces make it hard to replay failures or compare model versions.
- If agents are allowed to do deterministic math, the system becomes harder to test and drift becomes harder to detect.

## Next Improvements

- Split the workflow into explicit `ResearchAgent`, `RulesAgent`, `SkepticAgent`, and `ProbabilityAgent` modules.
- Add a HUD scenario layer that mirrors the Python subagent boundaries.
- Add structured step traces with timestamps, model IDs, and artifact references.
- Add migrations and normalized tables for markets, outcomes, and decisions.
- Add retry, timeout, and circuit-breaker policies around external calls.
- Add calibration reporting and archived-snapshot replay.

## Phased Build Plan

### Phase 1: Foundation

- Finalize schemas and storage contracts.
- Implement SQLite persistence, logging, config loading, and CLI workflows.
- Add deterministic example flow and unit tests for pricing/ranking.

### Phase 2: Live Market Ingestion

- Wire official Polymarket Gamma/Data/CLOB adapters.
- Add polling, snapshot retention, deduplication, and schema validation.
- Introduce market filters for liquidity, stale quotes, and malformed rules.

### Phase 3: Real Research Workflow

- Plug in search providers and source-specific collectors.
- Add claim extraction, source scoring, contradiction detection, and rule parsing.
- Swap heuristic probability estimation for configurable OpenAI-compatible synthesis.

### Phase 4: Signal Quality

- Improve ranking features, confidence calibration, and no-trade logic.
- Add theme exposure tracking, correlated market controls, and paper portfolio accounting.
- Persist execution decisions and decision-time context for later evaluation.

### Phase 5: Evaluation And Execution

- Build archived-snapshot replay and resolution outcome tracking.
- Add calibration reports, category-level PnL, and model comparison dashboards.
- Add optional real execution hooks only after paper-trading metrics look credible.

## What This Scaffold Includes Now

- Typed Pydantic schemas for normalized markets, research packets, and pricing outputs.
- Config via environment variables plus YAML overrides.
- HUD-first model provider configuration with an OpenAI-compatible adapter seam.
- Replaceable storage layer using SQLAlchemy and SQLite by default.
- Adapter stubs for Gamma API, Data API, and CLOB ingestion.
- Research collector and synthesis split.
- Agentic workflow with inspectable step logs and explicit target-outcome selection.
- Pricing, ranking, portfolio, execution, and evaluation modules.
- Repo-backed CLI flow for synced example markets instead of a purely in-memory loop.
- Persisted paper-trade ledger scaffold.
- CLI commands:
  - `sync-markets`
  - `research-market`
  - `rank-opportunities`
  - `run-daily-batch`
  - `evaluate-results`
  - `example-flow`
- Dockerfile and minimal tests.

## End-To-End Example Flow

The included example uses a static weather market to show the architecture without needing live credentials.

## Run Locally

```bash
cd polymarket_ai_system
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
polymarket-ai example-flow
```

The flow:

1. Builds a normalized example market.
2. Stores a market snapshot.
3. Runs research collection and synthesis.
4. Produces a probability estimate and final memo.
5. Ranks the opportunity.
6. Suggests a stake through portfolio constraints.
7. Creates and persists a paper trade only if it passes filters.

## Where To Plug In Search And Model Providers

- Search providers belong behind `research.collectors.SearchClient`.
- Source-specific collectors should live in `research/collectors.py` or split into one file per source family later.
- LLM or reasoning-model routing belongs behind `infra.providers.ModelProvider`.
- OpenAI-compatible or HUD-compatible clients should return structured probability outputs, not free-form prose.
- Keep extraction and classification on cheaper models; reserve the strongest model for synthesis and final probability estimation.
- The current HUD adapter assumes an OpenAI-compatible `chat/completions` surface and should be the first place you customize once you confirm your exact HUD deployment contract.

## What To Build First Vs Later

Build first:

- Live market ingestion for a narrow subset of markets.
- Confirm the exact HUD request/response contract and lock the provider adapter to that schema.
- Rule parsing and rule-risk checks.
- Source collection with strict citation storage.
- Evaluation logging at decision time.
- Calibration and no-trade thresholds.

Build later:

- Real execution.
- Advanced portfolio optimization.
- Correlated exposure management.
- Cross-market agent swarms.
- Anything UI-heavy.

## Reality Check

The biggest reasons systems like this fail:

- The market is usually more efficient than it looks once fees, spread, and slippage are included.
- Resolution criteria are misunderstood, causing false edge.
- Research quality is uneven and not reproducible.
- Models sound confident when evidence is thin or stale.
- Backtests overfit to archived winners and ignore markets you would not have selected in real time.
- Operational discipline breaks down and paper performance does not survive live execution friction.
- The best apparent opportunities cluster in illiquid or ambiguous markets where you cannot actually monetize the edge safely.

## Do Not Trust These Signals

- Markets driven mostly by memes, vibes, or anonymous social chatter.
- Tiny edge estimates that disappear after cost assumptions.
- Recommendations without explicit bear cases.
- Markets with ambiguous or changing resolution sources.
- Signals supported by a single source or single narrative chain.
- Highly attention-saturated markets unless your thesis is genuinely orthogonal.
- Model outputs that do not cite concrete dates, numbers, and official references.

## Next Implementation Steps

1. Wire the real Polymarket public endpoints into `market_data.adapters`.
2. Add archived snapshot readers and outcome resolvers for evaluation.
3. Implement actual web search and source fetch abstractions.
4. Add LLM-backed extraction and synthesis with schema-validated outputs.
5. Expand repositories to persist paper trades, score histories, and realized outcomes.
6. Add migration tooling such as Alembic once the first stable schema iteration settles.
7. Add integration tests for the end-to-end batch path.

## HUD Agent Layer

```text
Orchestrator -> RulesAgent -> ResearchAgent -> SkepticAgent -> ProbabilityAgent -> Decision
                |              |                |                |
                v              v                v                v
              tools         sources         counter-case      EV + filters
```

- `prediction_market_env` is the local HUD-style environment boundary.
- Tools are registered with `@env.tool()` and are intentionally narrow.
- Scenarios are the testable boundaries for each subagent.
- The orchestrator stays thin and delegates the real work to the subagents.

### Subagent Responsibilities

- `RulesAgent`: turn raw rules into explicit criteria and risks.
- `ResearchAgent`: gather evidence and produce a structured research summary.
- `SkepticAgent`: challenge the thesis and surface failure modes.
- `ProbabilityAgent`: combine the inputs into fair probability and a trade decision.

### How To Add A New Subagent

1. Add a structured input/output model in `src/polymarket_ai/hud/models.py`.
2. Add the agent implementation in `src/polymarket_ai/hud/agents.py`.
3. Register a scenario in `src/polymarket_ai/hud/scenarios.py`.
4. Wire it into `src/polymarket_ai/hud/orchestrator.py`.

### How To Run

```bash
python -m polymarket_ai.hud.cli analyze-market atlantic_hurricanes_over_15_2026
python -m polymarket_ai.hud.cli run_tests
python -m polymarket_ai.hud.cli run_eval_suite
```

### How To Plug Into HUD

- Set `POLYMARKET_AI_PROVIDER=hud`.
- Provide `POLYMARKET_AI_HUD_BASE_URL`, `POLYMARKET_AI_HUD_API_KEY`, and model names in `.env`.
- Replace the fallback logic in `src/polymarket_ai/infra/providers.py` when your HUD deployment contract is final.

## Failure Modes

- The system can still be wrong when resolution rules are ambiguous.
- Public source quality can be too thin to support a confident edge.
- A model can be well-structured and still be confidently mistaken.
- The market can already be efficient, leaving no live edge after costs.
- Deterministic fallback behavior will correctly avoid risk, but it can also suppress some real opportunities.

## Next Improvements

- Add a real HUD-backed model runtime with request/response telemetry.
- Persist run traces, retries, and agent outputs to the new repository layer.
- Replace the example market fallback with live market ingestion.
- Add correlation-aware portfolio sizing and paper-trade accounting.
- Expand scenario tests with known fixtures and golden outputs.
