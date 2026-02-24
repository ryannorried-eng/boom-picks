# Autonomous Sports Betting Analytics Platform — Execution Plan

## 1) Mission and Success Criteria

### Core mission
Build an autonomous sports betting analytics platform that identifies **+EV opportunities** for **paper trading** and proves a measurable edge over the market.

### Primary objective
Demonstrate that model-generated picks beat the market by producing **positive Market CLV over at least 100 settled picks**.

### Non-goals (for now)
- Do **not** place real-money bets.
- Do **not** change core sizing/modeling formulas unless data supports it.
- Do **not** optimize for volume at the expense of data quality.

---

## 2) Operating Loop (System Flywheel)

1. Ingest market odds from target books/exchanges.
2. Generate fair probabilities from proprietary models.
3. Detect mispricing (+EV picks) and publish picks with sizing.
4. Record line movement and track CLV against market close.
5. Settle results and evaluate edge quality.
6. Feed diagnostics back into reliability/modeling backlog.

Everything in the roadmap supports this loop.

---

## 3) Phased Delivery Plan

## Phase 0 — Baseline and Instrumentation (Week 1)

**Goal:** Ensure every pick can be audited end-to-end.

### Deliverables
- Canonical event schema across ingestion/model/picks/settlement.
- Unique pick lifecycle ID linking snapshot line → emitted pick → closing line → settlement.
- Core observability dashboard for:
  - ingestion freshness,
  - pick generation latency,
  - settlement lag,
  - CLV coverage (% picks with valid close line).

### Exit criteria
- 100% of new picks contain complete lineage metadata.
- Median pick generation latency and p95 latency are visible and alertable.

## Phase 1 — Reliability Hardening (Weeks 1–3)

**Goal:** Eliminate known operational issues before scaling pick volume.

### Priority fixes
1. **Home/away mapping reliability**
   - Introduce deterministic team normalization and alias table.
   - Add reconciliation checks (team + start time + league constraints).
   - Quarantine ambiguous events instead of force-matching.
2. **Pick generation latency**
   - Profile end-to-end critical path (odds poll → feature build → model inference → pick write).
   - Add asynchronous queueing and bounded retries.
   - Cache static/slow-moving features.

### Guardrails
- No pick is published if event mapping confidence is below threshold.
- Stale odds snapshots are ignored automatically.

### Exit criteria
- Mapping error rate below defined SLO (e.g., <0.5%).
- p95 pick generation latency meets target SLO.

## Phase 2 — Edge Validation Framework (Weeks 2–6)

**Goal:** Statistically evaluate whether the current system has an edge.

### Deliverables
- CLV framework with these views:
  - Opening vs pick line vs closing line,
  - Market CLV by sport/market/book/time-to-game,
  - Distribution and confidence intervals.
- Settlement attribution model:
  - ROI,
  - hit rate,
  - expected vs realized value,
  - volatility metrics.
- Minimum-sample governance:
  - formal checkpoint at 100 settled picks,
  - rolling evaluations every 25 additional settled picks.

### Decision gates
- **Gate A (100 settled picks):** positive aggregate Market CLV?
- **Gate B (stability):** CLV robust across segments (not one narrow slice only)?
- **Gate C (operational quality):** low missing-close and low mapping anomalies?

### Exit criteria
- A written “edge verdict” report template auto-generated from tracked metrics.

## Phase 3 — Dashboard Productization (Weeks 3–7)

**Goal:** Make picks and performance immediately actionable for a user.

### Deliverables
- Picks board with:
  - EV%, implied edge, confidence tier,
  - Kelly-based paper stake,
  - line-source timestamp.
- Performance module with:
  - CLV trend,
  - settled pick outcomes,
  - by-market segmentation.
- Parlay builder safeguards:
  - prevent correlated legs where applicable,
  - show blended EV and risk disclaimers.
- Reliability/status strip:
  - ingestion health,
  - model freshness,
  - delayed settlement indicators.

### Exit criteria
- A user can open the dashboard and answer in under 60 seconds:
  1) what are today’s top +EV picks?
  2) is the system beating close?
  3) are data pipelines healthy?

## Phase 4 — Multi-Sport Expansion (Weeks 6–12)

**Goal:** Extend the proven loop to new sports without degrading quality.

### Expansion strategy
- Add one new sport at a time (e.g., MLB, then NFL).
- Reuse common pipeline components:
  - ingestion adapters,
  - event normalization,
  - pick lifecycle tracking,
  - CLV/settlement framework.
- Keep sport-specific model logic isolated.

### Entry requirements for each new sport
- Sufficient historical data coverage.
- Stable event/entity mapping.
- Baseline backtest sanity checks.

### Exit criteria per sport
- Sport-specific CLV and settlement dashboards live.
- No regression to NBA pipeline SLOs.

---

## 4) KPI Tree (What Success Looks Like)

## North-star KPI
- **Market CLV (aggregate) over settled picks** with confidence bounds.

## Supporting KPIs
- Data quality:
  - % picks with valid close line,
  - mapping anomaly rate,
  - stale-odds discard rate.
- Latency and uptime:
  - poll-to-pick p50/p95,
  - pipeline success rate,
  - auto-retry recovery rate.
- Outcome diagnostics:
  - ROI (paper),
  - realized vs expected edge,
  - drawdown and variance.
- Product usage (if internal/external users):
  - time-to-first-actionable-pick,
  - dashboard load and refresh reliability.

---

## 5) Governance and Change Control

- Freeze Kelly formula and core model architecture until the 100+ settled-pick checkpoint unless there is a critical correctness bug.
- Version every model/pipeline change and annotate affected picks.
- Use pre-defined review cadence:
  - weekly reliability review,
  - biweekly edge review,
  - monthly expansion review.

---

## 6) Risks and Mitigations

1. **False edge from bad mapping or stale lines**
   - Mitigation: strict data-quality gates, quarantine workflows.
2. **Small sample overconfidence**
   - Mitigation: confidence intervals and minimum-sample gates.
3. **Latency causing missed numbers**
   - Mitigation: p95 SLOs, queue prioritization, performance profiling.
4. **Expansion too early**
   - Mitigation: strict phase gates tied to validated NBA edge and reliability.

---

## 7) Immediate 30-Day Action Plan

### Week 1
- Finalize pick lifecycle schema and lineage IDs.
- Stand up reliability + CLV instrumentation.
- Define SLO thresholds for mapping and latency.

### Week 2
- Ship home/away mapping hardening and ambiguity quarantine.
- Ship latency optimizations and stale-line protections.

### Week 3
- Complete CLV and settlement attribution dashboards.
- Run first formal edge checkpoint with current settled sample.

### Week 4
- Tighten dashboard UX for top-pick discovery and performance clarity.
- Publish first monthly “edge status” report and decision memo.

---

## 8) Definition of Done (Program Level)

The program is successful when all of the following are true:
- Fully autonomous pipeline runs with minimal intervention and meets reliability SLOs.
- At least 100 settled paper picks are evaluated with complete CLV coverage.
- Aggregate Market CLV is positive and reasonably robust across segments.
- Dashboard presents actionable +EV opportunities and transparent performance diagnostics.
- Expansion playbook is documented and ready for the next sport.
