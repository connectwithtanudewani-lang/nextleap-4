"""Streamlit UI for the PPFAS facts-only FAQ assistant.

Run: streamlit run app.py
Nothing the user types is written to disk or logged; chat history lives only
in the browser session, and messages containing PII are masked even there.
"""
import streamlit as st

from rag import llm
from rag.assistant import DISCLAIMER, Assistant

st.set_page_config(page_title="MF Facts · PPFAS", page_icon="📄", layout="centered")

EXAMPLES = {  # button label -> full question sent
    "Exit load of the Flexi Cap Fund?": "What is the exit load of Parag Parikh Flexi Cap Fund?",
    "ELSS Tax Saver lock-in?": "What is the lock-in for Parag Parikh ELSS Tax Saver Fund?",
    "Get my capital-gains statement?": "How do I download my capital-gains statement?",
}
AVATAR = {"user": "🙂", "assistant": "📄"}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500&display=swap');
html, body, [class*="css"], .stMarkdown, .stChatMessage { font-family: 'Inter', sans-serif; }
.stApp { background: #F6F3EC; }
h1.mast { font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 2.1rem;
          color: #1D2B26; letter-spacing: -0.01em; margin: 0.2rem 0 0.1rem; }
p.sub { color: #4A574F; font-size: 1rem; margin: 0 0 0.9rem; }
.note { display: inline-block; border: 1px solid #1E5B4B; color: #1E5B4B; border-radius: 3px;
        padding: 2px 9px; font-size: 0.8rem; font-weight: 500; letter-spacing: 0.02em; }
.scope { color: #6B746E; font-size: 0.83rem; margin-top: 0.6rem; }
div.stButton > button { background: #FFFDF8; border: 1px solid #D8D1C2; color: #1D2B26;
        border-radius: 4px; text-align: left; font-size: 0.88rem; width: 100%; }
div.stButton > button:hover { border-color: #1E5B4B; color: #1E5B4B; }
.stChatMessage { background: #FFFDF8; border: 1px solid #E6E0D3; border-radius: 6px; }
.stChatMessage a { color: #1E5B4B; }
footer, #MainMenu { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_assistant():
    return Assistant()


bot = get_assistant()

st.markdown('<h1 class="mast">Mutual fund facts, straight from the source.</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub">Ask about expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark '
    "or statements — every answer links the official page it came from.</p>",
    unsafe_allow_html=True,
)
st.markdown(f'<span class="note">{DISCLAIMER}</span>', unsafe_allow_html=True)
st.markdown(
    '<p class="scope">Covers PPFAS Mutual Fund: Parag Parikh Flexi Cap, ELSS Tax Saver, Large Cap and Liquid Fund. '
    "Sources: PPFAS AMC, AMFI and SEBI pages only. Please don't enter PAN, Aadhaar, account numbers, OTPs, emails or phone numbers.</p>",
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

st.write("")
st.caption("Try one:")
cols = st.columns(3)
clicked = None
for col, (label, q) in zip(cols, EXAMPLES.items()):
    if col.button(label, use_container_width=True):
        clicked = q

for role, content in st.session_state.history:
    with st.chat_message(role, avatar=AVATAR[role]):
        st.markdown(content)

typed = st.chat_input("Ask a factual question about a PPFAS scheme…")
question = typed or clicked

if question:
    reply = bot.ask(question)
    shown_q = "_[message hidden — it contained personal details]_" if reply.kind == "refusal_pii" else question
    st.session_state.history.append(("user", shown_q))
    st.session_state.history.append(("assistant", reply.as_markdown()))
    with st.chat_message("user", avatar=AVATAR["user"]):
        st.markdown(shown_q)
    with st.chat_message("assistant", avatar=AVATAR["assistant"]):
        st.markdown(reply.as_markdown())

mode = llm.provider() or "extractive (no LLM key)"
st.markdown(f'<p class="scope">Answer mode: {mode}. Facts are retrieved, never generated from memory.</p>',
            unsafe_allow_html=True)
