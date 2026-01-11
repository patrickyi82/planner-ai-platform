# Roadmap

This is the living plan for `planner-ai-platform`.

## North Star

A platform that can:

1. Load a plan (YAML/JSON) + project “pack”
2. Expand outcomes/milestones into tasks using module templates + prompts
3. Lint the result against a standard delivery framework (coverage, gates, DoD quality, dependency DAG)
4. Export tasks/checks as artifacts (Markdown, JSON) and later optionally create GitHub issues

---

## Phase 0 — Repo scaffolding and working agreements

**Goal:** stable foundation so every later step is incremental.

**Acceptance**
- You can run a “hello planner” command locally
- Clear “in scope now vs later” list

---

## Phase 1 — Minimal plan schema (v0) + parser/validator

**Goal:** represent a plan in a strict, typed way so it’s lintable and expandable.

**Acceptance**
- `planner validate examples/basic-plan.yaml` passes
- Bad input produces actionable errors

---

## Phase 2 — Standard Delivery Framework (SDF) v0 + linter

**Goal:** enforce “holistic and consistent” plans across domains.

**Acceptance**
- `planner lint examples/basic-plan.yaml` returns PASS or actionable missing items

---

## Phase 3 — Expansion engine v0 (deterministic first)

**Acceptance**
- `planner expand examples/outcome-health.yaml` generates a bigger plan

---

## Phase 4 — AI-assisted expansion

**Acceptance**
- AI-generated tasks are categorized, verifiable, and pass lints (or get patch suggestions)

---

## Phase 5 — Project pack support

**Acceptance**
- Point at a project folder and run validate/expand/lint

---

## Phase 6 — Output + integrations

Pick one at a time:
- Export Markdown reports
- Export JSON
- GitHub issues creation
- UI viewer
