# Product Improvements

## 1. Five Weaknesses in the Current Design

1. **No report caching or deduplication.** Submitting the same company twice runs the full workflow again, burning API credits and time. There's no fingerprinting on `(company_name, objective)` to return a cached report.
2. **Sequential research.** The Researcher node processes each sub-task one-by-one. Five searches take 5× the time of one; parallelising with `asyncio.gather` would cut research time by ~60%.
3. **Quality score is self-reported.** The QualityCheck node uses Claude to score Claude's own output — a conflict of interest that inflates scores. An independent rubric-based evaluation or human-in-the-loop checkpoint would be more reliable.
4. **No export or sharing.** Users can't export a report as PDF or share a URL. For a sales-prep tool, AEs need to forward the brief to their manager or paste it into Salesforce before a call.
5. **Chat has no memory summarisation.** The full report JSON is injected as a system prompt on every chat turn (~3–8k tokens). Long conversations will hit context limits and cost grows linearly. Sliding window summarisation is needed.

---

## 2. Top 3 Improvements to Build Next (Prioritised)

### Priority 1 — Parallel research + incremental streaming
The single highest-impact engineering improvement. Fan out sub-task searches concurrently (LangGraph `Send` API + `asyncio.gather`), stream each section to the UI as it's written by the Analyst. Perceived latency drops from "wait 3 minutes" to "first section appears in 30 seconds". This directly improves activation and reduces abandonment.

### Priority 2 — Report export (PDF + CRM push)
AEs need the brief _inside_ their workflow, not in a separate tool. A one-click PDF export + a Salesforce/HubSpot push button turns ZyLabs from a research toy into a sales enablement platform. This is the unlock for enterprise deals and willingness to pay.

### Priority 3 — Report templates / personas
Different users need different angles. A VP Sales briefing before a board call needs different sections than an SDR cold-calling a prospect. Let users pick a template (Sales Call Prep, Competitive Intel, Investment Brief) that adjusts the 9 sections, Planner prompts, and Analyst persona. Increases perceived value and drives repeat usage.

---

## 3. Buyer vs User — Distinction and Willingness to Pay

**Buyer (VP Sales / RevOps):**
- Cares about: time saved per rep, pipeline velocity, win rate lift, integration with existing stack (Salesforce, Outreach, Gong).
- Willingness to pay: **$50–150/seat/month** if they can show "ZyLabs saved X hours of pre-call research → Y% more meetings booked". Buys as a team licence, measured against quota attainment.
- Key objection: "Why not just Google?" — they need a ROI number, not a demo.

**User (AE / SDR):**
- Cares about: speed ("brief me in 2 minutes"), accuracy ("don't hallucinate the CEO's name"), ease ("one click before a call").
- Willingness to pay: **$15–30/month individually** if the company doesn't pay. More likely to expense it if their manager doesn't know the tool exists.
- Key objection: "I'll just use ChatGPT" — they need the workflow to be meaningfully faster and more structured than a free tool.

**Insight:** Sell top-down to VP Sales on ROI metrics, but design the product for the AE who will actually use it daily. The AE is the champion who convinces the VP to sign the PO.

---

## 4. Success Metrics

| Metric | Definition | Target (Month 3) |
|--------|-----------|-----------------|
| Sessions created | # of research sessions started per active user per week | ≥ 3/user/week |
| Report quality score | Average QualityCheck score across completed reports | ≥ 80/100 |
| Time-to-briefing | Seconds from "Start Research" click to report fully rendered | ≤ 90s (P50) |
| Chat engagement rate | % of sessions where user sends ≥ 1 follow-up message | ≥ 40% |
| Report export rate | % of completed reports exported to PDF or pushed to CRM | ≥ 20% |
| 7-day retention | % of users who return within 7 days of first session | ≥ 50% |

---

## 5. 4-Week AI Roadmap

**Week 1 — Speed & reliability**
- Parallel research (fan-out sub-tasks with `Send` API)
- Streaming section-by-section render on the frontend
- Retry with exponential backoff for Tavily + Anthropic API errors
- Report fingerprint cache (skip re-run for same company+objective)

**Week 2 — Quality & trust**
- Independent quality evaluator (separate Claude call with a rubric, not self-scoring)
- Source confidence scoring (prioritise authoritative domains)
- Hallucination guard: flag claims the Researcher found no evidence for
- Human-in-the-loop: "Request re-research" button on any section

**Week 3 — Workflow & integrations**
- PDF export (Playwright headless rendering)
- Salesforce / HubSpot one-click push (OAuth connector)
- Report templates (Sales Call, Competitive Intel, Investment Brief)
- Slack notification when report is ready

**Week 4 — Scale & enterprise**
- Auth (Auth0/Clerk) + team workspaces
- Per-team API key management
- Admin dashboard: usage, cost per session, team-level metrics
- PostgreSQL migration + multi-worker deployment

---

## 6. Biggest Cost / Scaling / Reliability Risks

**Cost:** Each report runs 4+ Claude API calls (Planner, Analyst, QualityCheck, ReportGenerator) + 5–6 Tavily searches. At current pricing, one report costs ~$0.08–0.15 in API fees. At 10,000 reports/month, that's $800–1,500/month in API costs before infrastructure. Quality retries can double the cost for low-quality initial outputs. Mitigation: cache reports aggressively, use `claude-haiku-4-5` for QualityCheck (cheaper, sufficient for scoring), add daily/monthly per-user caps.

**Scaling:** SQLite single-writer lock prevents horizontal scaling. A single `uvicorn` worker handles concurrent SSE streams via asyncio, but adding workers requires PostgreSQL. LangGraph workflows are CPU-light but I/O-heavy; a single-worker server can handle ~20 concurrent workflows before latency degrades. Mitigation: move to PostgreSQL + stateless workers + a task queue (Celery/ARQ) for workflow execution.

**Reliability:** External API dependency on both Anthropic and Tavily means a failure in either service fails the entire workflow. Tavily outages are more frequent. Mitigation: graceful degradation (continue with partial findings if Tavily fails), circuit breaker with cached results, fallback to DuckDuckGo/SerpAPI for search.

---

## 7. Feature to Remove + Feature to Add

**Remove:** The QA retry loop that routes back to the Researcher (currently up to 2 retries). In practice, a second Tavily search on the same gaps rarely produces meaningfully better data — Tavily's index hasn't changed in 60 seconds. The retries add 60–120 seconds of latency for marginal quality gain. Better to invest that time in a stronger Analyst prompt that synthesises partial data more confidently.

**Add:** **"Compare companies" mode.** Let users submit 2–3 companies and generate a side-by-side competitive brief. This is the single most-requested feature in competitive intelligence tools and maps directly to "I'm preparing to pitch against Competitor X". It's a natural extension of the existing single-company workflow (run N graphs in parallel, add a synthesis node).

---

## 8. First 90-Day Roadmap

**Days 1–30 (Find product-market fit):**
- Launch with 20 design-partner AEs at 5 target companies (freemium, no auth)
- Instrument every session: time-to-briefing, quality score, chat messages sent
- Weekly 30-min interviews: what sections are useless? what's missing?
- Ship: PDF export, streaming render, parallel research

**Days 31–60 (Drive retention):**
- Auth + team workspaces (stops "who is this random user?" problem)
- Salesforce push (drives retention — report lives in the CRM, not just ZyLabs)
- Report templates (Sales Call Prep is the killer use case — build it first)
- Ship: hallucination guard, source citations with confidence scores

**Days 61–90 (Monetise):**
- Launch paid plans: Free (5 reports/month), Pro ($49/month, unlimited), Team ($149/seat, CRM integrations)
- Conversion experiment: free-to-paid email sequence triggered at 4th report
- Ship: Compare companies mode, Slack integration
- Target: 50 paying users, $5k MRR

---

## 9. What I'd Change First as Product Owner

**I'd replace the quality score gate with user feedback loops.**

The QualityCheck node currently routes the workflow algorithmically based on a Claude-assigned score. This is a heuristic that optimises for "completeness" but not for "does this actually help the AE close a deal?" Those are very different things.

Instead, I'd add explicit thumbs-up/thumbs-down buttons on each report section and track which sections users copy-paste (a strong signal they found them useful). After 500 sessions, I'd have a real dataset to fine-tune the Analyst prompt and section weights — replacing the current self-scoring loop with empirical evidence of what AEs actually read and use. Product iteration speed from real user signals beats algorithmic quality gates.

This shift — from "AI scores itself" to "users score the AI" — is the foundational move that turns ZyLabs from a demo into a product.
