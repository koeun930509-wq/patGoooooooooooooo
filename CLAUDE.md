# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**PetGo** (반려동물 동반 여행 가이드) is a Streamlit MVP that solves "헛걸음" — pet owners getting turned away at a destination because pet-entry rules were unclear. Given a pet's profile (breed, weight, dangerous-breed status, muzzle-wearability) and a place's raw Korean-language pet policy text from a government API, it produces one of four verdicts (🟢 가능 / 🟡 조건부 가능 / 🔴 불가 / ⚪ 정보 부족), a plain-language reason, a required-items checklist, and cautions — always citing the source text, never inventing conditions that aren't in it.

Two planning docs are the source of truth for scope and rules — read them before changing behavior, not just this file:
- `PRD_반려동물동반여행가이드.md` — full PRD (functional requirements, API field semantics, judgment rules §8, risks §14).
- `개발프롬프트.md` — contains the **exact system prompt** used by the LLM interpreter (section B), verbatim in `pet_guide/llm_interpreter.py`. Don't reword that prompt without updating both places.

## Commands

```bash
pip install -r requirements.txt
streamlit run app.py          # run the app locally (needs .env with SERVICE_KEY at minimum)
pytest tests/ -v               # run judge-engine unit tests (no network/API keys needed)
pytest tests/test_judge.py::test_dangerous_breed_lodging_requires_muzzle -v   # single test
```

Copy `.env.example` to `.env` and fill in `SERVICE_KEY` (data.go.kr) to exercise real API calls; `ANTHROPIC_API_KEY` is optional — without it, ambiguous cases fall back to "정보 부족" instead of calling Claude.

## Architecture

**Two-stage judgment pipeline (`pet_guide/judge.py` → `pet_guide/llm_interpreter.py`)** is the core of the app and the piece most likely to need changes:
1. `judge.py::_apply_rules()` tries deterministic Korean-keyword/regex rules first (explicit disallow keywords, numeric `"Nkg 이하"` weight limits, 소/중/대형 size categories via `SIZE_WEIGHT_THRESHOLDS`, 맹견+입마개 combos, 일부구역/실외 restrictions, all-empty-fields → 정보 부족). It returns a `JudgeResult`, or `None` if nothing matched (genuinely ambiguous free text).
2. Only on `None` does `judge_pet()` lazily import and call `llm_interpreter.interpret()`, which sends the pet profile + raw `detailPetTour2` fields to Claude using the fixed system prompt from `개발프롬프트.md`. This exists specifically to conserve the API's daily quota and to keep verdicts deterministic wherever a rule can decide it — LLM calls are the exception path, not the default.
3. If no `ANTHROPIC_API_KEY` is set, or the call fails, it falls back to `"정보 부족"` rather than guessing — see `PRD §14` risk table ("LLM 환각" mitigation).

When adding a new rule, add it inside `_apply_rules()`'s `hits` list (severity 1=가능, 2=조건부 가능, 3=불가) rather than short-circuiting — multiple rules can fire for one place, and the highest-severity hit wins while reasons/checklist/cautions from all hits are merged.

**Service key never reaches the client.** `pet_guide/api_client.py` is the only module allowed to read `SERVICE_KEY`/call `apis.data.go.kr`. Because Streamlit executes entirely server-side, this file being the sole key-holder is sufficient — there's no separate BFF layer to maintain, unlike the React+Node split the original spec sketched (deliberately not used here; see below).

**Caching is load-bearing, not an optimization.** The dev `SERVICE_KEY` account is capped at 1,000 calls/day (`PRD §11`). Every `api_client.py` function wrapping a TourAPI call is `@st.cache_data(ttl=3600)` — don't remove this without replacing it with something equivalent.

**`detailIntro2` field names vary by `contentTypeId`** (a 음식점's opening-hours field has a different key than a 관광지's). `api_client.get_place_detail()` handles this via `_first_present()` scanning a list of known field-name variants (`_USE_TIME_FIELDS`, `_REST_DATE_FIELDS`, `_PARKING_FIELDS`) rather than a single hardcoded key — extend those lists if a new content type surfaces a new field name.

**UI is single-process Streamlit, not React+BFF.** The original spec draft (embedded in `개발프롬프트.md`) proposed a React/TypeScript frontend with a separate Node BFF; that was explicitly decided against in favor of one Streamlit app (`app.py` routes between `pet_guide/ui/{profile,explore,detail}_screen.py` via `st.sidebar.radio`, state lives in `st.session_state`) for MVP simplicity. Screens communicate via `st.session_state` keys (`pets`, `companion_indices`, `selected_place`, `search_results`, `nav`) initialized in `app.py` — check that dict before adding new cross-screen state.

**Judging is per-pet, not per-trip.** `detail_screen.py` re-runs `judge_pet()` once per selected companion animal (a place can be fine for one dog and wrong for another in the same party), not once for the group.
