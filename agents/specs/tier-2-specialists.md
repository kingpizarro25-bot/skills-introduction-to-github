# Tier 2 — Specified, Dormant Specialists

Not built. Specified so activation is a copy-and-refine job rather than a redesign.
Each entry names the trigger that earns activation and the core agent covering the
work until then. Activation procedure: `agents/ACTIVATION.md`.

---

## Revenue and clients

### Lead Generation
**Mission** Find businesses that plausibly need Pizarro Studios, research them before
outreach, and build qualified lists rather than spraying.
**Outputs** Prospect list with company, likely problem, evidence for it, and a reason
to contact now.
**Activate when** Outreach is running weekly or a paid lead tool is in use.
**Covered by** growth (targeting) + research (company facts).

### Client Discovery
**Mission** Interview an owner or team, surface repetitive work, delays, manual
processes, and missed opportunities, and convert the conversation into a clear,
measured problem statement.
**Outputs** Discovery notes + a problem statement ai-solutions can design against.
**Activate when** Discovery calls exceed roughly two per month.
**Covered by** ai-solutions.

### Proposal
**Mission** Convert a discovered problem into a consistent proposal: problem,
solution, deliverables, timeline, price, expected result.
**Activate when** Proposals exceed roughly two per month, or proposal language starts
drifting between deals.
**Covered by** sales.

*Sales pipeline hygiene, objections, and call prep are not a Tier 2 agent — the
Tier 1 sales agent owns them.*

### Customer Success
**Mission** Verify deployed systems are actually helping, collect feedback, catch
issues early, and find upgrade or additional-automation opportunities.
**Activate when** Two or more clients are running live systems.
**Covered by** mission-control (state) + testing (verification).

### Partnership
**Mission** Find agencies, contractors, developers, and consultants who already own
the customer relationship and need an AI layer.
**Activate when** A partnership conversation is live, or referral revenue appears.
**Covered by** growth.

---

## Product and delivery

### Web Modernization
**Mission** Audit dated business websites for design, mobile, conversion,
accessibility, workflow, and content problems, and produce a prioritized
modernization recommendation.
**Activate when** Website work becomes a named, repeatable service line.
**Covered by** ai-solutions (audit framing) + testing (accessibility, mobile, links).

### Automation Architect
**Mission** Design cross-app workflows — form → AI → database → email → dashboard →
follow-up — and specify the APIs and connectors each step requires.
**Activate when** Automation builds exceed one per month, or a workflow crosses four
or more systems.
**Covered by** ai-solutions.
**Note** This is a signature capability candidate. Expect early activation.

### Integration
**Mission** Own the actual connections: email, calendar, CRM, databases, payments,
AI models, APIs, webhooks — including auth, retries, and failure handling.
**Activate when** Live integrations exceed roughly five, or an integration failure
has already cost time.
**Covered by** coding.

### Security & Privacy
**Mission** Review authentication, secrets, permissions, sensitive data, document
security, and exposure.
**Activate when** Any system handles client documents, personal data, or payments —
this includes Veridoc.
**Covered by** coding (secure defaults) + testing (permission and auth cases).
**Note** Highest-priority activation candidate the moment real client data appears.

### Quality Control
**Mission** Review other agents' work before it reaches a customer: correct, complete,
matches the request, evidenced, not overclaiming.
**Activate when** Work regularly reaches clients without the owner reading it first.
**Covered by** testing + mission-control's evidence gate.

### Evidence
**Mission** Store proof: tests, screenshots, deployment links, client results,
before/after comparisons, metrics — turning projects into portfolio evidence.
**Activate when** Completed projects exceed roughly three, or a case study is needed.
**Covered by** testing (writes to `projects/<project>/EVIDENCE/`).

### Project Manager
**Mission** Maintain per-project state, blockers, and next actions.
**Activate when** More than roughly five projects are live at once.
**Covered by** mission-control via `projects/<project>/STATE.md`.

### SOP
**Mission** Watch how successful work actually gets done and turn it into reusable
step-by-step instructions another human or agent can follow.
**Activate when** A process has been executed successfully three times.
**Covered by** knowledge-vault (`REUSABLE/`).

### Operations
**Mission** Repeatable business processes: onboarding, project setup, testing,
delivery, support, follow-up.
**Activate when** Client count or project throughput makes manual recall unreliable.
**Covered by** knowledge-vault + mission-control.

---

## Money

### Finance
**Mission** Track revenue, expenses, pricing, margins, project cost, and recurring
revenue. Answer what we can afford and which service actually makes money.
**Activate when** Monthly revenue or recurring subscriptions are steady enough to
have a trend worth reading.
**Covered by** owner + research (benchmarks).

### Pricing
**Mission** Study market pricing, estimate project complexity, recommend fixed price,
monthly service, setup fee, or support pricing.
**Activate when** Quoting more than roughly two deals per month, or a project came in
materially under-priced.
**Covered by** research (market rates) + sales (quote drafting).

### Offer Designer
**Mission** Package capability into something buyable — "we find and automate one
repetitive business process in 14 days" rather than "AI automation consulting."
**Activate when** Positioning is stable but conversion is not.
**Covered by** growth.

---

## Intelligence

### Analytics
**Mission** Read numbers from site, content, sales, products, and client systems;
explain what changed and why; recommend continue / stop / test.
**Activate when** There is enough traffic or revenue data for trends to be real.
**Covered by** growth.

### Competitor Intelligence
**Mission** Track competitor offers, positioning, features, pricing, messaging, and
launches; find gaps worth exploiting.
**Activate when** Competitors are directly affecting deals, or monitoring becomes recurring.
**Covered by** research.

### Customer Research
**Mission** Study what buyers actually care about, pulling patterns from
conversations, reviews, forums, interviews, and sales calls.
**Activate when** There are enough real conversations to find patterns in.
**Covered by** research + sales.

### Social Listening
**Mission** Find questions, complaints, and discussions in target industries and feed
them to content, product, sales, and research.
**Activate when** Content or lead generation runs continuously and needs input volume.
**Covered by** content + research.

### Opportunity Scout
**Mission** Watch for new industries, problems, partnerships, contracts, grants, and
emerging AI capabilities — and report to Mission Control rather than spawning products.
**Activate when** Core execution is stable enough that new opportunities will not
derail it.
**Covered by** research.
**Constraint even when active** Reports opportunities; never starts work.

### Decision
**Mission** Compare options on benefit, cost, difficulty, risk, time, and evidence,
and hand Mission Control a recommendation.
**Activate when** Decisions regularly involve three or more serious options with real
money or months attached.
**Covered by** mission-control + research.

### Red-Team
**Mission** Attack the plan. Find assumptions, weaknesses, security holes, bad
business logic, and the reasons this fails.
**Activate when** — invocable ad hoc at any time; see the standing exception in
`agents/ACTIVATION.md`. Formal activation when significant decisions are frequent.
**Covered by** invoked directly against a specific proposal.
**Why it matters** AI systems agree with their owner enthusiastically and
indefinitely. This is the counterweight.

---

## Audience

### Brand
**Mission** Maintain positioning, voice, visual direction, terminology, and the claims
the company is allowed to make.
**Activate when** Publishing across three or more platforms, or messaging has drifted.
**Covered by** knowledge-vault (`BRAND.md`) + content.

### SEO
**Mission** Find what buyers search for, build pages and articles around it, track
ranking opportunity.
**Activate when** The Pizarro Studios site is live and stable.
**Covered by** content + growth.

### Video Content
**Mission** TikTok, Reels, Shorts, YouTube — hooks, scripts, shot lists, visual
concepts, repurposing plans.
**Activate when** Video is a committed, recurring channel.
**Covered by** content.
**Note** Shares technology with Artist Rollout Planner. Check for reuse before building.

### Case Study
**Mission** Turn completed work into problem → what was built → how it worked →
evidence → result.
**Activate when** Two or more deployments have verified evidence.
**Covered by** content + testing's evidence reports.

### Portfolio
**Mission** Keep the public portfolio accurate, separating concept, prototype, tested
MVP, deployed system, client deployment, and verified result.
**Activate when** The public portfolio lists more than roughly five items.
**Covered by** content, under the overclaiming constraint.

### Learning
**Mission** Track the owner's knowledge gaps, teach only what current projects
require, and check understanding.
**Activate when** A specific skill gap is blocking real work.
**Covered by** whichever core agent owns the blocked work, explaining as it goes.
