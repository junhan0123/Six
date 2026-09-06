# Changelog

All notable changes to Xiao6 will be documented in this file.

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