# Product Improvements

## 1. Five Weaknesses in the Current Design

1. **No report caching or deduplication.**
   Submitting the same company twice triggers a full workflow re-run, consuming all API quota and taking 2–3 minutes again. There is no fingerprinting on `(company_name, objective)` hash to return a cached report. At free-tier quota levels, this is a meaningful waste.

2. **Sequential research is slow.**
   The Researcher node runs each Tavily sub-task one after another. Five sub-tasks at ~2s each = 10s of search time, plus website scrape. Parallelising with `asyncio.gather` (or LangGraph's `Send` API) would reduce research wall-clock time by ~60% and make the workflow feel substantially faster.

3. **Self-reported quality score.**
   The QualityCheck node uses `gemini-2.5-flash` to score `gemini-2.5-flash`'s own output. This is a structural conflict of interest — the model has an incentive to score highly to avoid re-work, and scores consistently land in the 75–90 range regardless of actual quality. An independent rubric-based evaluator or user-feedback signal would be more reliable.

4. **No export or sharing.**
   Users cannot export a report as PDF, copy it as Markdown, or share a URL. For a sales-prep tool, the AE needs to forward the brief to their manager or paste it into Salesforce before a call. Without export, the report lives only inside ZyLabs — limiting its utility in existing workflows.

5. **Chat context has no summarisation.**
   The full `final_report` JSON (~3–8k tokens) is injected as a Gemini system instruction on every chat turn. Long conversations increase cost linearly and will eventually hit context limits. A sliding-window summariser that compresses older turns into a running summary would solve both problems.

---

## 2. Top 3 Improvements to Build Next

### Priority 1 — Parallel research + streaming section render

**What:** Use LangGraph's `Send` API to fan out Researcher sub-tasks concurrently, and stream each Analyst section to the UI as it's written rather than waiting for all 9.

**Why it matters:** This is the single highest-impact UX improvement. The current workflow feels like a black box for 2–3 minutes. Streaming the first section within 30 seconds of clicking "Start Research" — while the rest continue generating — transforms the experience from "waiting" to "watching". It directly reduces abandonment on the first session (the highest-risk moment for activation).

**Effort:** ~2 days. Parallelising the Researcher node is a LangGraph `Send` API change. Streaming sections requires the Analyst to emit partial state on each section completion — achievable by splitting the Analyst into a loop of 9 individual section calls.

### Priority 2 — PDF export + CRM push

**What:** One-click PDF export (Playwright headless rendering of the report page) and a Salesforce/HubSpot OAuth connector to push the report as a contact note.

**Why it matters:** AEs don't live in ZyLabs — they live in Salesforce. A report that can't leave the browser isn't part of the sales workflow; it's a novelty. PDF export and CRM push are the features that turn a demo into a tool people pay for and use every day. This is the unlock for enterprise licence deals — VP Sales will sign a PO for a tool that lives inside their existing stack.

**Effort:** ~3 days. PDF via `playwright` + `report_pdf` endpoint. Salesforce push via OAuth2 PKCE flow + REST API `POST /sobjects/Note`.

### Priority 3 — Research templates

**What:** Let users select a template before starting — Sales Call Prep, Competitive Intelligence, Investment Brief — which adjusts the Planner prompt, the 9 section definitions, and the Analyst persona.

**Why it matters:** A Sales Call Prep brief for an AE (focus: pain points, recent news, decision-maker names) is completely different from a Competitive Intel brief for a product manager (focus: feature comparison, pricing, roadmap). Forcing both through the same 9-section template produces a mediocre report for both. Templates increase perceived value with no additional API cost and drive repeat usage ("I use Sales Call Prep every day, and now I want to try the Investment Brief template").

**Effort:** ~1 day. Add a `template` field to the session creation form, pass it to the Planner and Analyst prompts, store it on the `Session` model.

---

## 3. Buyer vs User — Distinction and Willingness to Pay

### Buyer: VP Sales / RevOps

- **Goal:** Increase pipeline velocity and win rate without adding headcount.
- **Decision criteria:** ROI, not features. They need to show "ZyLabs saved X hours of prep per rep per week → Y% more calls booked → $Z incremental pipeline".
- **Willingness to pay:** **$50–150 / seat / month** as a team licence. Buys in bulk (10–50 seats). Measures success against quota attainment, not user satisfaction scores.
- **Key objection:** "Why not just Google?" — they need a number, not a demo. The first conversation should lead with time-saved-per-rep calculation.
- **Key purchase trigger:** Integration with Salesforce. If the report auto-populates a Salesforce record before a call, the VP can see utilisation in CRM reports and tie it to pipeline outcomes.

### User: AE / SDR

- **Goal:** Show up to every call more prepared than the prospect expects, in the least time possible.
- **Decision criteria:** Speed, accuracy, ease. "Give me a brief in under 2 minutes, and don't make up the CEO's name."
- **Willingness to pay:** **$15–30 / month** individually. Will expense it without telling their manager if it saves them 30 minutes before a big call. More price-sensitive than the buyer.
- **Key objection:** "I'll just use ChatGPT." They need the workflow to be meaningfully faster and more structured — a blank ChatGPT prompt requires them to know what to ask. ZyLabs asks it for them.
- **Key retention driver:** The first time a prospect says "wow, you really did your homework" — that's the moment the AE becomes a permanent user and internal champion.

**Strategic insight:** Sell top-down to VP Sales on ROI metrics to get the PO signed. Design bottom-up for the AE so the product is used daily. The AE is both the daily user and the internal champion who convinces the VP the renewal is worth it.

---

## 4. Success Metrics

| Metric | Definition | Target (Month 3) |
|--------|-----------|-----------------|
| Sessions created per user | Research sessions started per active user per week | ≥ 3 / user / week |
| Report completion rate | % of triggered workflow runs that produce a `complete` status | ≥ 90% |
| Report quality score | Average `quality_score` across all completed reports | ≥ 80 / 100 |
| Time-to-briefing (P50) | Seconds from "Start Research" click to report fully rendered | ≤ 90s |
| Chat engagement rate | % of sessions where user sends ≥ 1 follow-up message | ≥ 40% |
| Report export rate | % of completed reports exported or shared | ≥ 20% |
| 7-day retention | % of users who return within 7 days of first session | ≥ 50% |
| Free → paid conversion | % of free users who upgrade within 30 days | ≥ 8% |

**Leading indicator to watch first:** Time-to-briefing. Everything else follows from whether users trust the workflow to produce a useful brief before they need it. If this number is > 3 minutes, activation will be low regardless of report quality.

---

## 5. 4-Week AI Roadmap

### Week 1 — Speed & reliability

- **Parallel research:** Fan out Researcher sub-tasks with LangGraph `Send` API + `asyncio.gather` — target 60% reduction in research wall-clock time
- **Streaming section render:** Stream each Analyst section to the UI as it completes — first section visible within 30s
- **Report fingerprint cache:** Skip re-run for `(company_name, objective)` combos seen in the last 7 days
- **Async Gemini retries:** Replace `time.sleep()` in `gemini.py` with `asyncio.sleep()` so the event loop is not blocked during 429 backoff

### Week 2 — Quality & trust

- **Independent quality evaluator:** Separate Gemini call with a strict rubric (not self-scoring). Score each section independently on a 10-point scale.
- **Source confidence scoring:** Weight Tavily results by domain authority — prefer official company pages, SEC filings, reputable press
- **Hallucination guard:** Flag report claims that have no matching evidence in `raw_findings` (simple string overlap heuristic as a first pass)
- **"Request re-research" button:** Let users flag a specific section as inadequate and trigger a targeted re-run of just that section

### Week 3 — Integrations & export

- **PDF export:** Playwright headless render of the report page → `GET /sessions/:id/export.pdf`
- **Salesforce push:** OAuth2 PKCE connector → push report as a Salesforce Contact note pre-call
- **HubSpot push:** Same pattern via HubSpot Contacts API
- **Report templates:** Sales Call Prep / Competitive Intel / Investment Brief — adjusts Planner prompts and section definitions
- **Slack notification:** Webhook when report is ready — "Your Stripe brief is ready 📋"

### Week 4 — Scale & auth

- **Authentication:** Auth0 or Clerk — JWT-based, session ownership checks on all endpoints
- **Team workspaces:** Shared session library, visibility controls (private / team / public)
- **Per-user API key management:** Teams bring their own Gemini / Tavily keys → no platform API cost
- **PostgreSQL migration:** Replace SQLite with managed PostgreSQL (Railway / Supabase) — Alembic migrations, async sessions
- **Admin dashboard:** Usage per user, cost per session (token count × model pricing), error rate, quality score distribution

---

## 6. Biggest Cost / Scaling / Reliability Risks

### Cost

Each report run makes 3 Gemini API calls (Planner, Analyst, QualityCheck) + 4–6 Tavily searches. On Gemini free tier this is $0. On a paid Gemini plan at `gemini-2.5-flash` pricing, one report costs roughly **$0.05–0.12** in tokens. Quality retries (up to 2×) can triple cost for low-quality initial outputs.

At 10,000 reports/month on a paid plan: **$500–1,200/month in API costs** before infrastructure. Mitigations: aggressive report caching, `gemini-2.0-flash-lite` for QualityCheck (cheaper, sufficient for scoring), per-user daily run caps.

### Scaling

SQLite's single-writer lock is the first scaling wall. A single `uvicorn` worker handles ~20 concurrent SSE streams efficiently via `asyncio`, but adding workers (`--workers N`) requires PostgreSQL. The per-session `asyncio.Queue` lives in process memory — SSE streaming only works in single-worker mode.

LangGraph workflows are I/O-heavy (waiting on Gemini + Tavily) rather than CPU-heavy, so a single async worker scales further than it appears. For production: PostgreSQL + stateless workers + a task queue (ARQ or Celery) for workflow execution, decoupled from the HTTP layer.

### Reliability

The workflow has two hard external dependencies: Gemini API and Tavily Search. A Gemini outage fails the entire workflow. A Tavily outage degrades research quality but can be handled gracefully (the Researcher node catches per-task Tavily failures and continues with partial findings).

Mitigations:
- Gemini: 3× retry with backoff (already implemented). Fallback model chain (`gemini-2.5-flash` → `gemini-2.0-flash-lite`) as a next step.
- Tavily: fallback to SerpAPI or DuckDuckGo if Tavily returns an error.
- Both: circuit breaker that returns the last cached report for a company if all retries fail.

---

## 7. Feature to Remove + Feature to Add

### Remove: the QA retry loop (2× re-research)

In practice, a second Tavily search on the same gaps rarely produces meaningfully better data — Tavily's index hasn't changed in the 30 seconds since the first search. The retries add 60–120 seconds of latency for marginal quality gain and double the Tavily quota usage. Better investment: a stronger Analyst prompt that synthesises partial data more confidently, and a "Request re-research" button that lets users trigger a targeted re-run on a specific section when they actually want it.

### Add: "Compare companies" mode

Let users submit 2–3 companies and generate a side-by-side competitive brief: same 9 sections, rendered as a comparison table. This is the single most-requested feature in competitive intelligence tools. It maps directly to "I'm preparing to pitch against Competitor X" — the exact moment a sales tool earns its keep. Implementation: run N single-company graphs in parallel (already the architecture), add a synthesis node that generates a `comparison_table` section. Estimated effort: 2 days.

---

## 8. First 90-Day Roadmap

### Days 1–30: Find product-market fit

- Launch freemium (no auth) with **20 design-partner AEs** at 5 target B2B companies
- Instrument every session: time-to-briefing, quality score, report sections viewed, chat messages sent
- Weekly 30-min user interviews: "Which sections did you actually use? What was missing? Did you open ZyLabs before your last call?"
- Ship in week 2: PDF export + streaming section render (the two features most likely to change "cool demo" → "I need this before every call")
- Ship in week 3: parallel research (cut time-to-briefing to < 90s)

### Days 31–60: Drive retention

- Add Auth0 authentication + team workspaces (stops "who is this user?" — makes usage measurable per rep)
- Salesforce push integration (report lives in CRM → retention is automatic)
- Ship: Report templates — Sales Call Prep as the first template (highest-frequency use case)
- Ship: Hallucination guard + source confidence scores (builds trust — AEs need to be confident citing the report in front of a prospect)

### Days 61–90: Monetise

- Launch paid tiers:
  - **Free:** 5 reports/month, no export
  - **Pro ($29/month):** unlimited reports + PDF export
  - **Team ($99/seat/month):** CRM integrations + shared workspace + admin dashboard
- Conversion trigger: free-to-paid email sequence triggered at the 4th report ("You've already used ZyLabs for 4 calls — upgrade to get PDF export and Salesforce sync")
- Ship: Compare companies mode
- Target end of Day 90: **50 paying users, $3–5k MRR**

---

## 9. What I'd Change First as Product Owner

**I'd replace the algorithmic quality gate with user feedback signals.**

The QualityCheck node routes the workflow based on a Gemini-assigned score. This optimises for "completeness" — are all 9 sections non-empty? — but says nothing about whether the report actually helps an AE close a deal. Those are fundamentally different things, and optimising for the wrong metric at the core of the product leads to a tool that feels thorough but isn't trusted.

My first change as product owner: add **thumbs-up / thumbs-down buttons on each report section** and track which sections users highlight, copy, or share. After 200 sessions, I'd have a real signal — "AEs never read the Technology & Infrastructure section, but they always copy the Strategic Insights section." That data would let me:

1. Re-weight the Analyst prompt to invest more tokens in high-value sections
2. Replace the QualityCheck self-score with a rubric trained on actual user feedback
3. Consider removing low-engagement sections and replacing them with ones users actually want (e.g. "Key Decision Makers", "Recent Customer Reviews")

The shift from "AI scores itself" to "users score the AI" is the foundational product move that turns ZyLabs from a technically impressive demo into a tool people trust enough to use before a $500k deal.
