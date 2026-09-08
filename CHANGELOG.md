# Changelog

All notable changes to Xiao6 will be documented in this file.

---

## [1.1.0] - 2026-09-08

### Added

#### GFE Intelligence Modules
- gfe_sources — Source manager and reliability calculator
- gfe_events — Event intelligence engine
- gfe_history — Historical comparison engine
- gfe_causal — Causal graph engine
- gfe_intelligence — Unified GFE intelligence interface
- gfe_forecast — Forecast engine with scenario analysis
- gfe_forecast_ledger — Prediction ledger
- gfe_warning — Early warning engine
- gfe_calibration — Calibration engine
- gfe_analyst_council — Multi-analyst consensus
- gfe_scenario — Scenario generation and evaluation
- gfe_world_state — World state tracking

#### Services
- observation_service — Observation service for task lifecycle events
- proposal_service — Proposal service for autonomous task proposals
- proposal_task_adapter — Adapter between proposals and tasks
- proposal_validator — Proposal validation logic

#### Tests
- test_phase140.py — World state engine tests
- test_phase141.py — Event intelligence tests
- test_phase142.py — Historical comparison tests
- test_phase143.py — Causal graph tests
- test_phase144.py — Analyst council tests
- test_phase145.py — Scenario engine tests
- test_phase146.py — Forecast engine tests
- test_phase147.py — Forecast ledger tests
- test_phase148.py — Early warning tests
- test_phase149.py — Calibration tests
- test_phase150.py — GFE integration tests
- test_phase151.py — E2E integration tests
- test_phase152.py — Production acceptance tests

#### Tooling
- scripts/preflight.sh — Deployment preflight check script
- .env.example — Environment configuration template

### Changed

- VERSION bumped to 1.1.0
- Audit and completion reports archived to docs/audit/

### API

- `/api/observation/status` — Observation service status
- `/api/proposals` — Proposal management endpoints
- `/api/self_awareness/status` — Self-awareness status
- `/api/self_awareness/run` — Run self-awareness check
- `/api/self_awareness/decide` — Decision endpoint

---

## [1.0.0] - 2026-09-06

### Added

#### S143 Foundation
- Memory Intelligence Layer (S143.1)
- Knowledge Intelligence Layer (S143.2)
- World Model Foundation (S143.3)
- Proactive Intelligence Foundation (S143.4)
- Architecture Freeze Declaration (S143.5)

#### S144 Interaction & Intelligence Feed
- Command Parser (S144.1)
- Intent Router (S144.1)
- Interaction Context (S144.1)
- Response Builder (S144.1)
- Interaction System (S144.1)
- Activity Tracker (S144.2)
- Command Bar UI (S144.2)
- Intelligence Feed (S144.3)
- Ranking Engine (S144.4)
- Memory Loop Feedback (S144.5)

#### S145-S150 Intelligence Layers
- Foresight Engine (S145) — Trend Detection, Early Warning
- Context Engine (S146) — Event Relation Mapping, Causal Graph
- Reasoning Engine (S147) — Evidence Chain, Snapshot
- Decision Engine (S148) — Option Analysis, Risk/Benefit
- Prediction Ledger (S149) — Prediction Lifecycle, Verification
- Learning Engine (S150) — Accuracy Analysis, Source Reliability

#### S151-S153 Consolidation
- Intelligence Center Consolidation (S151)
- Stabilization Audit (S152)
- Release Freeze (S153)

### API Changes

**New Endpoints:**
- `GET /api/intelligence/feed`
- `GET /api/intelligence/foresight`
- `GET /api/intelligence/context`
- `GET /api/intelligence/reasoning`
- `GET /api/intelligence/decision`
- `GET /api/intelligence/predictions`
- `POST /api/intelligence/predictions/verify`
- `GET /api/intelligence/learning`
- `GET /api/intelligence/center`
- `GET /api/interaction/status`
- `POST /api/interaction/parse`
- `GET /api/interaction/activity`

### UI Changes

**New Components:**
- AI Insight Center (7 Tabs)
  - [洞察] — Feed + Ranking
  - [趋势] — Foresight
  - [关联] — Context
  - [推理] — Reasoning
  - [决策] — Decision
  - [预测] — Prediction
  - [学习] — Learning
- Command Bar
- Activity Center Panel

### Technical

- 63 tools mounted
- 330 knowledge nodes, 112 relations
- Python 3.11.9 runtime
- SQLite database

---

## [Unreleased]

_No unreleased changes._