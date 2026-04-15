# MIS Final Project (MVP)

This repository contains a Streamlit MVP for an AI-powered learning system that challenges student reasoning.

## Current MVP Scope

- Working Streamlit interface
- Engagement Trigger pre-step for stuck learners
- One functioning agent: **Intellectual Sparring Partner**
- Thinking-focused interaction (counterargument, weakness, probing questions)
- Guidance fade levels (High, Medium, Low)
- Progress panel with revision history and simple reasoning heuristics
- Anti-answer guardrails (the app refuses to write final submissions)
- Streamlit first-run onboarding bypass via local `.streamlit/credentials.toml`

## Setup

```bash
pip install streamlit openai python-dotenv
```

## Run

```bash
python -m streamlit run app.py
```

## Notes

- If `OPENAI_API_KEY` is not set, the app uses a fallback local response so the demo still works.
- To disable Streamlit telemetry prompts, `.streamlit/config.toml` sets:
  - `gatherUsageStats = false`
