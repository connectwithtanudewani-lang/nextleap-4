"""Streamlit UI for the PPFAS facts-only FAQ assistant (dark, chat-only).

Run: streamlit run app.py
Sources and retrieval run in the backend (rag/); the UI is just the chat.
Nothing the user types is written to disk or logged; history lives only in
the browser session, and messages containing PII are masked even there.
"""
from html import escape

import streamlit as st

from rag.assistant import Assistant, fmt_date

st.set_page_config(page_title="MF Facts assistant", page_icon="💬", layout="centered")

EXAMPLES = {  # chip label -> full question sent
    "Exit load of Flexi Cap?": "What is the exit load of Parag Parikh Flexi Cap Fund?",
    "ELSS lock-in period?": "What is the lock-in for Parag Parikh ELSS Tax Saver Fund?",
    "How to get my capital-gains statement?": "How do I download my capital-gains statement?",
}
REFUSALS = {"refusal_advice", "refusal_pii", "performance", "out_of_scope"}
REFUSAL_LABEL = {
    "refusal_advice": "Not advice",
    "refusal_pii": "Personal details blocked",
    "performance": "No return figures",
    "out_of_scope": "Out of scope",
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, .stApp, [class*="css"], .stMarkdown, button, input, textarea { font-family: 'Inter', system-ui, sans-serif !important; }
.stApp { background: #0B0C0F; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], #MainMenu, footer { display: none !important; }
.block-container { max-width: 820px; padding-top: 1.2rem; padding-bottom: 7rem; }

/* header */
.mf-head { display:flex; align-items:center; gap:12px; padding: 4px 0 16px; }
.mf-logo { width:40px; height:40px; border-radius:50%; background:#2F6BFF; display:flex; align-items:center; justify-content:center; flex:0 0 auto; }
.mf-title { font-weight:600; font-size:16px; color:#E7E9EE; line-height:1.3; }
.mf-status { font-size:12px; color:#8FD3A8; }
.mf-rule { border:none; border-top:1px solid #1E2127; margin: 0 0 22px; }

/* messages */
.mf-row { display:flex; gap:12px; align-items:flex-start; margin: 0 0 18px; }
.mf-av { width:32px; height:32px; border-radius:50%; background:#172440; color:#7FA6FF; font-size:11px; font-weight:700;
         display:flex; align-items:center; justify-content:center; flex:0 0 auto; }
.mf-bot { background:#181B21; border:1px solid #23272F; border-radius:4px 14px 14px 14px; padding:14px 16px;
          font-size:15px; line-height:1.6; color:#E7E9EE; max-width:88%; }
.mf-warn { background:#1D1A12; border-color:#3B3220; }
.mf-tag { font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:#E7B95C; margin-bottom:6px; }
.mf-foot { display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px; font-size:12px; color:#8A909C;
           border-top:1px solid #23272F; margin-top:12px; padding-top:10px; }
.mf-foot a, .mf-bot a { color:#7FA6FF !important; text-decoration:none; font-weight:500; }
.mf-foot a:hover { color:#A9C3FF !important; }
.mf-user { display:flex; justify-content:flex-end; margin: 0 0 18px; }
.mf-user div { background:#2F6BFF; color:#FFFFFF; border-radius:14px 14px 4px 14px; padding:12px 16px; font-size:15px; max-width:80%; line-height:1.5; }
.mf-chips-gap { margin-left:44px; }

/* chips + new chat button */
div.stButton > button { background:#111317; border:1px solid #2A2E36; color:#C9CDD6; border-radius:999px;
        font-size:13px; padding:8px 14px; min-height:44px; }
div.stButton > button:hover { border-color:#2F6BFF; color:#FFFFFF; background:#151A26; }
div.stButton > button:focus:not(:active) { border-color:#2F6BFF; color:#FFFFFF; }

/* input bar */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background:#0B0C0F !important; }
[data-testid="stBottom"] { border-top:1px solid #1E2127; }
[data-testid="stChatInput"] { background:#0B0C0F !important; border:1px solid #2A2E36 !important; border-radius:14px !important; }
[data-testid="stChatInput"] textarea { color:#E7E9EE !important; font-size:15px !important; }
[data-testid="stChatInputSubmitButton"] { background:#2F6BFF !important; border-radius:10px !important; }
[data-testid="stChatInputSubmitButton"] svg { fill:#FFFFFF !important; color:#FFFFFF !important; }
.mf-disc { text-align:center; font-size:12px; color:#8A909C; margin-top:-4px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_assistant():
    return Assistant()


bot = get_assistant()
if "history" not in st.session_state:
    st.session_state.history = []  # list of ("user", text) / ("bot", Reply)

# ---------- header ----------
left, right = st.columns([5, 1.3], vertical_alignment="center")
with left:
    st.markdown(
        """<div class="mf-head"><div class="mf-logo"><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"
        fill="none" stroke="#FFFFFF" stroke-width="1.8"><path d="M5 5h14v10H9l-4 4z"/></svg></div>
        <div><div class="mf-title">MF Facts assistant</div><div class="mf-status">● Facts-only · PPFAS Mutual Fund</div></div></div>""",
        unsafe_allow_html=True,
    )
with right:
    if st.button("＋ New chat", use_container_width=True):
        st.session_state.history = []
        st.rerun()
st.markdown('<hr class="mf-rule">', unsafe_allow_html=True)


# ---------- rendering ----------
def bot_bubble(inner, warn=False):
    cls = "mf-bot mf-warn" if warn else "mf-bot"
    st.markdown(f'<div class="mf-row"><div class="mf-av">MF</div><div class="{cls}">{inner}</div></div>',
                unsafe_allow_html=True)


def render_reply(r):
    warn = r.kind in REFUSALS
    tag = f'<div class="mf-tag">{REFUSAL_LABEL[r.kind]}</div>' if warn else ""
    label = "Learn" if r.kind == "refusal_advice" else "Source"
    foot = (f'<div class="mf-foot"><a href="{escape(r.source_url)}" target="_blank" rel="noopener">'
            f'{label}: {escape(r.source_title)} ↗</a>'
            f'<span>Last updated from sources: {fmt_date(r.as_of)}</span></div>')
    bot_bubble(f"{tag}{escape(r.text)}{foot}", warn)


def render_user(text):
    st.markdown(f'<div class="mf-user"><div>{escape(text)}</div></div>', unsafe_allow_html=True)


# ---------- welcome + chips ----------
bot_bubble("Hi! I answer factual questions about Parag Parikh Flexi Cap, ELSS Tax Saver, Large Cap and "
           "Liquid Fund — expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark and "
           "statements — using only official PPFAS, AMFI and SEBI pages.")
clicked = None
chip_cols = st.columns([1, 1, 1.5])
for col, (label, q) in zip(chip_cols, EXAMPLES.items()):
    if col.button(label, use_container_width=True):
        clicked = q
st.write("")

# ---------- conversation ----------
for role, item in st.session_state.history:
    if role == "user":
        render_user(item)
    else:
        render_reply(item)

typed = st.chat_input("Ask about a PPFAS scheme…")
question = typed or clicked
if question:
    reply = bot.ask(question)
    shown = "[message hidden — it contained personal details]" if reply.kind == "refusal_pii" else question
    st.session_state.history += [("user", shown), ("bot", reply)]
    render_user(shown)
    render_reply(reply)

with getattr(st, "bottom", None) or st._bottom:  # st.bottom on newer Streamlit
    st.markdown('<div class="mf-disc">Facts-only. No investment advice. Please don\'t share PAN, Aadhaar, '
                "OTPs, phone, email or account numbers.</div>", unsafe_allow_html=True)
