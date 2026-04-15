import os
from datetime import datetime

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="MIS Final Project", page_icon="🧠", layout="centered")

st.title("MIS Final Project")
st.subheader("Thinking Coach MVP")

st.markdown(
    """
This app is designed to increase **thinking effort**.

Current flow:
1. Choose your starting mode.
2. If you're stuck, complete a quick engagement trigger.
3. Get a reasoning challenge and revise your claim.
"""
)

if "engagement_summary" not in st.session_state:
    st.session_state.engagement_summary = ""

if "history" not in st.session_state:
    st.session_state.history = []

mode = st.radio(
    "Step 1: Where are you right now?",
    options=["I have a draft claim", "I'm stuck and need help starting"],
)

if mode == "I'm stuck and need help starting":
    st.markdown("### Engagement Trigger")
    unclear = st.text_area("What is unclear?", height=80)
    goal = st.text_area("What is the goal?", height=80)
    tried = st.text_area("What have you tried?", height=80)

    if st.button("Save my starting context"):
        st.session_state.engagement_summary = (
            f"What is unclear: {unclear.strip()}\n"
            f"Goal: {goal.strip()}\n"
            f"What was tried: {tried.strip()}"
        )
        st.success("Saved. Now write your draft claim below and run the sparring step.")

round_count = len(st.session_state.history)
if round_count >= 4:
    suggested_level = "Low"
elif round_count >= 2:
    suggested_level = "Medium"
else:
    suggested_level = "High"

st.caption(f"Suggested guidance level for this round: **{suggested_level}**")
guidance_level = st.selectbox("Step 2: Guidance level", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(suggested_level))

st.caption("This tool challenges your reasoning and will not write your final submission for you.")

user_claim = st.text_area(
    "Step 3: Write your current claim, argument, or solution draft:",
    height=180,
    placeholder="Example: Schools should replace final exams with project-based assessments.",
)

run_clicked = st.button("Challenge my reasoning")


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
        "I can help you think it through instead:\n"
        "1. What is your current position in one sentence?\n"
        "2. What evidence supports it?\n"
        "3. What is the strongest counterargument you need to answer?"
    )


def format_sections_by_guidance(base_counter: str, base_weakness: str, questions: list[str], level: str) -> str:
    if level == "High":
        return (
            f"**Counterargument:** {base_counter}\n\n"
            f"**Potential Weakness:** {base_weakness}\n\n"
            "**Probing Questions:**\n"
            + "\n".join(f"{idx + 1}. {q}" for idx, q in enumerate(questions[:3]))
        )
    if level == "Medium":
        return (
            f"**Core Challenge:** {base_counter}\n\n"
            f"**Main Weakness:** {base_weakness}\n\n"
            "**Focus Questions:**\n"
            + "\n".join(f"{idx + 1}. {q}" for idx, q in enumerate(questions[:2]))
        )
    return f"**Single Challenge Question:** {questions[0]}"


def fallback_sparring_response(text: str, context_summary: str, level: str) -> str:
    if looks_like_answer_request(text):
        return coaching_refusal_message()

    counter = "Your claim may overgeneralize and ignore edge cases where the opposite approach works better."
    weakness = "The reasoning does not yet include clear evidence, tradeoffs, or implementation constraints."
    questions = [
        "What is the strongest argument against your position?",
        "Which assumptions in your argument could be false?",
        "What evidence would convince a skeptic?",
    ]

    response = format_sections_by_guidance(counter, weakness, questions, level)

    if context_summary.strip() and level != "Low":
        response += "\n\n**Context from your engagement trigger:**\n" + context_summary

    return response


def openai_sparring_response(text: str, context_summary: str, level: str) -> str:
    if looks_like_answer_request(text):
        return coaching_refusal_message()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key.strip():
        return fallback_sparring_response(text, context_summary, level)

    client = OpenAI(api_key=api_key)

    context_block = (
        f"\nEngagement trigger context:\n{context_summary}\n"
        if context_summary
        else ""
    )

    scaffolding = {
        "High": "Use full structure with Counterargument, Potential Weakness, and exactly 3 Probing Questions.",
        "Medium": "Use concise structure with Core Challenge, Main Weakness, and exactly 2 Focus Questions.",
        "Low": "Use minimal structure: provide exactly one strong challenge question and no other sections.",
    }[level]

    prompt = f"""
You are an Intellectual Sparring Partner.
Your goal is to challenge thinking, not provide final answers.
Never write the user's final submission, final essay, or completed assignment.
If the user asks you to write the answer for them, refuse and provide coaching questions only.

User claim:
{text}
{context_block}
{scaffolding}

Keep it concise, clear, and academically respectful.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.7,
    )

    return response.output_text.strip()


def show_progress_panel(current_claim: str) -> None:
    st.markdown("### Progress")
    rounds = len(st.session_state.history)

    evidence_words = ["evidence", "data", "study", "source", "statistic", "research"]
    tradeoff_words = ["tradeoff", "cost", "constraint", "risk", "limitation", "feasible"]

    current_text = current_claim.lower()
    has_evidence = any(word in current_text for word in evidence_words)
    has_tradeoff = any(word in current_text for word in tradeoff_words)

    st.write(f"Revision rounds: **{rounds}**")
    st.write(f"Evidence language detected: **{'Yes' if has_evidence else 'No'}**")
    st.write(f"Tradeoff/constraint language detected: **{'Yes' if has_tradeoff else 'No'}**")

    if rounds >= 2:
        previous_claim = st.session_state.history[-2]["claim"]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Previous claim**")
            st.code(previous_claim)
        with col2:
            st.markdown("**Current claim**")
            st.code(current_claim)


if run_clicked:
    if not user_claim.strip():
        st.warning("Please enter a claim first.")
    else:
        with st.spinner("Generating challenge..."):
            challenge = openai_sparring_response(
                user_claim,
                st.session_state.engagement_summary.strip(),
                guidance_level,
            )

        st.session_state.history.append(
            {
                "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "claim": user_claim,
                "response": challenge,
                "guidance_level": guidance_level,
            }
        )

        st.markdown("### Sparring Output")
        st.markdown(challenge)
        show_progress_panel(user_claim)
        st.info("Next step: Revise your claim using the challenge above, then run it again.")
