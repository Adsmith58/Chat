import os
from datetime import datetime

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="MIS Final Project", page_icon="🧠", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.2rem; max-width: 1000px;}
.chat-note {background:#f6f8fa; border:1px solid #e6e8eb; border-radius:10px; padding:12px;}
.metric-card {background:#fbfcfe; border:1px solid #e6e8eb; border-radius:10px; padding:10px;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("MIS Final Project")
st.subheader("Professor-Mentor Thinking Coach")

if "engagement_summary" not in st.session_state:
    st.session_state.engagement_summary = ""
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome. I will challenge and strengthen your reasoning like a structured professor-mentor. "
                "I will not do your work for you. Start by sharing your current claim or draft."
            ),
        }
    ]


def looks_like_answer_request(text: str) -> bool:
    patterns = [
        "write this for me",
        "do it for me",
        "give me the final answer",
        "complete this assignment",
        "write my essay",
        "finish this for me",
    ]
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def coaching_refusal_message() -> str:
    return (
        "I can’t write the final submission for you.\n\n"
        "I can mentor your thinking instead:\n"
        "1. What is your current thesis in one sentence?\n"
        "2. What is your best evidence?\n"
        "3. What is the strongest objection you must answer?"
    )


def format_structured_response(level: str, challenge: str, weakness: str, questions: list[str], next_action: str) -> str:
    if level == "High":
        return (
            f"### 1) Socratic Pushback\n{challenge}\n\n"
            f"### 2) Method Weakness\n{weakness}\n\n"
            "### 3) Probing Questions\n"
            + "\n".join(f"- {q}" for q in questions[:3])
            + f"\n\n### 4) Next Revision Action\n{next_action}"
        )
    if level == "Medium":
        return (
            f"### Core Pushback\n{challenge}\n\n"
            f"### Key Weakness\n{weakness}\n\n"
            "### Focus Questions\n"
            + "\n".join(f"- {q}" for q in questions[:2])
            + f"\n\n### Next Revision Action\n{next_action}"
        )
    return f"### Single High-Impact Question\n{questions[0]}\n\n### Next Revision Action\n{next_action}"


def fallback_response(user_text: str, context_summary: str, level: str) -> str:
    if looks_like_answer_request(user_text):
        return coaching_refusal_message()

    challenge = "Your current reasoning may overgeneralize and does not yet account for serious edge cases."
    weakness = "The argument needs stronger evidence and a clearer treatment of tradeoffs and implementation limits."
    questions = [
        "What is the strongest counterexample to your claim?",
        "Which assumption, if false, would break your argument?",
        "What evidence would convince a skeptical professor?",
    ]
    next_action = "Rewrite your claim in 2–3 sentences including one tradeoff and one concrete piece of evidence."

    response = format_structured_response(level, challenge, weakness, questions, next_action)
    if context_summary.strip() and level != "Low":
        response += f"\n\n---\n**Context considered:**\n{context_summary}"
    return response


def openai_response(user_text: str, context_summary: str, level: str, recent_messages: list[dict]) -> str:
    if looks_like_answer_request(user_text):
        return coaching_refusal_message()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key.strip():
        return fallback_response(user_text, context_summary, level)

    scaffolding = {
        "High": "Return 4 markdown sections: 1) Socratic Pushback, 2) Method Weakness, 3) 3 Probing Questions, 4) Next Revision Action.",
        "Medium": "Return 4 concise sections: Core Pushback, Key Weakness, 2 Focus Questions, Next Revision Action.",
        "Low": "Return exactly 2 sections: Single High-Impact Question and Next Revision Action.",
    }[level]

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in recent_messages[-6:])
    context_block = f"Engagement trigger context:\n{context_summary}\n" if context_summary.strip() else ""

    prompt = f"""
You are a high-level professor and mentor.
Goal: strengthen the student's reasoning through structured critique.
Do NOT write final submissions, final essays, or completed assignments.
If the user asks for direct completion, refuse and switch to coaching questions.

{scaffolding}
Tone: clear, rigorous, encouraging.

Recent chat:
{transcript}

Current user message:
{user_text}

{context_block}
"""

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.6,
    )
    return response.output_text.strip()


def compute_metrics(text: str) -> tuple[bool, bool]:
    lowered = text.lower()
    evidence_words = ["evidence", "data", "study", "source", "statistic", "research"]
    tradeoff_words = ["tradeoff", "cost", "constraint", "risk", "limitation", "feasible"]
    return any(w in lowered for w in evidence_words), any(w in lowered for w in tradeoff_words)


with st.sidebar:
    st.markdown("### Mentor Settings")

    mode = st.radio(
        "Where are you right now?",
        options=["I have a draft claim", "I'm stuck and need help starting"],
    )

    rounds = len(st.session_state.history)
    suggested = "Low" if rounds >= 4 else "Medium" if rounds >= 2 else "High"
    st.caption(f"Suggested guidance level: **{suggested}**")
    guidance_level = st.selectbox("Guidance level", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(suggested))

    if st.button("Reset chat session"):
        st.session_state.history = []
        st.session_state.engagement_summary = ""
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Session reset. Share your current claim, and I will challenge your reasoning with structured guidance."
                ),
            }
        ]
        st.rerun()

if mode == "I'm stuck and need help starting":
    with st.expander("Engagement Trigger (start here if stuck)", expanded=True):
        unclear = st.text_area("What is unclear?", height=70)
        goal = st.text_area("What is the goal?", height=70)
        tried = st.text_area("What have you tried?", height=70)
        if st.button("Save starting context"):
            st.session_state.engagement_summary = (
                f"What is unclear: {unclear.strip()}\n"
                f"Goal: {goal.strip()}\n"
                f"What was tried: {tried.strip()}"
            )
            st.success("Saved. Continue in the chat below.")

st.markdown('<div class="chat-note">This coach is designed to enhance your thinking, not replace your work.</div>', unsafe_allow_html=True)

for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Share your current reasoning, draft, or question...")

if user_input:
    st.session_state.chat_messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your reasoning..."):
            mentor_reply = openai_response(
                user_input,
                st.session_state.engagement_summary.strip(),
                guidance_level,
                st.session_state.chat_messages,
            )
        st.markdown(mentor_reply)

    st.session_state.chat_messages.append({"role": "assistant", "content": mentor_reply})
    has_evidence, has_tradeoffs = compute_metrics(user_input)
    st.session_state.history.append(
        {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "claim": user_input,
            "response": mentor_reply,
            "guidance_level": guidance_level,
            "evidence_detected": has_evidence,
            "tradeoffs_detected": has_tradeoffs,
        }
    )

if st.session_state.history:
    latest = st.session_state.history[-1]
    st.markdown("### Progress Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card">Rounds<br><b>{len(st.session_state.history)}</b></div>', unsafe_allow_html=True)
    c2.markdown(
        f'<div class="metric-card">Evidence language<br><b>{"Yes" if latest["evidence_detected"] else "No"}</b></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="metric-card">Tradeoff language<br><b>{"Yes" if latest["tradeoffs_detected"] else "No"}</b></div>',
        unsafe_allow_html=True,
    )

    if len(st.session_state.history) >= 2:
        previous = st.session_state.history[-2]["claim"]
        current = st.session_state.history[-1]["claim"]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Previous input**")
            st.code(previous)
        with col2:
            st.markdown("**Current input**")
            st.code(current)
