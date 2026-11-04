"""Streamlit UI for the PPFAS facts-only FAQ assistant ("Sunrise" violet design).

Run: streamlit run app.py
Sources and retrieval run in the backend (rag/); the UI is just the chat.
Empty chat -> hero + suggestion cards (ChatGPT-style). After the first
question the hero gives way to the conversation.
Nothing the user types is written to disk or logged; history lives only in
the browser session, and messages containing PII are masked even there.
"""
from html import escape

import streamlit as st

from rag.assistant import Assistant, fmt_date

st.set_page_config(page_title="MF Facts", page_icon="💬", layout="centered")

SUGGESTIONS = [  # (icon, card label, question sent)
    (":material/percent:", "**Expense ratio**  \nFlexi Cap, Direct vs Regular",
     "What is the expense ratio of Parag Parikh Flexi Cap Fund?"),
    (":material/lock_clock:", "**ELSS lock-in**  \nHow long each SIP is locked",
     "What is the lock-in for Parag Parikh ELSS Tax Saver Fund?"),
    (":material/logout:", "**Exit load**  \nLiquid Fund, day by day",
     "What is the exit load of Parag Parikh Liquid Fund?"),
    (":material/description:", "**Capital-gains statement**  \nDownload it for tax filing",
     "How do I download my capital-gains statement?"),
]
REFUSAL_LABEL = {
    "refusal_advice": "I don't give advice",
    "refusal_pii": "Personal details blocked",
    "performance": "No return figures",
    "out_of_scope": "Out of scope",
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stApp *:not([data-testid="stIconMaterial"]) { font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important; }
.stApp { background: #F7F6FF; color: #17142B; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], #MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
.block-container { max-width: 800px; padding-top: 1rem; padding-bottom: 8rem; }

/* top bar */
.mf-brand { display:flex; align-items:center; gap:10px; min-height:44px; }
.mf-logo { width:34px; height:34px; border-radius:10px; background:#5B3FD6; color:#fff; font-weight:800; font-size:14px;
           display:flex; align-items:center; justify-content:center; }
.mf-name { font-weight:700; font-size:17px; color:#17142B; }
.mf-pill { font-size:12px; font-weight:600; color:#2B4FB8; background:#E3EBFF; padding:4px 10px; border-radius:999px; }

/* hero */
.mf-hero { text-align:center; padding: 44px 0 18px; }
.mf-dots { display:flex; gap:6px; justify-content:center; margin-bottom:22px; }
.mf-dots span { width:14px; height:14px; border-radius:50%; display:inline-block; }
.mf-hero h1 { font-size:40px !important; line-height:1.15 !important; font-weight:800 !important; letter-spacing:-0.025em;
              color:#17142B !important; margin:0 0 12px !important; padding:0 !important; }
.mf-hero p { font-size:16px; color:#575272; margin:0; }
.mf-covers { text-align:center; font-size:13px; color:#575272; margin-top:14px; }
.mf-covers b { color:#17142B; font-weight:600; }

/* buttons: suggestion cards + new chat */
div.stButton > button { background:#FFFFFF; border:1px solid #E4E0F7; color:#17142B; border-radius:18px;
        padding:14px 16px; min-height:44px; justify-content:flex-start; text-align:left; box-shadow:none; }
div.stButton > button > div { justify-content:flex-start; gap:12px; width:100%; }
div.stButton > button [data-testid="stMarkdownContainer"] { text-align:left; }
div.stButton > button p { font-size:13px; color:#575272; line-height:1.45; text-align:left; }
div.stButton > button strong { font-size:15px; color:#17142B; font-weight:700; }
div.stButton > button [data-testid="stIconMaterial"] { color:#5B3FD6; background:#ECE7FF; border-radius:10px; padding:7px; font-size:20px; }
div.stButton > button:hover { border-color:#5B3FD6; background:#FBFAFF; color:#17142B; }
div.stButton > button:focus:not(:active) { border-color:#5B3FD6; color:#17142B; }
.st-key-newchat button { border-radius:999px; padding:8px 16px; }
.st-key-newchat button > div { justify-content:center; gap:6px; }
.st-key-newchat [data-testid="stIconMaterial"] { background:none !important; padding:0 !important; font-size:18px !important; }
.st-key-newchat button p { color:#17142B; font-weight:600; font-size:14px; }

/* conversation */
.mf-user { display:flex; justify-content:flex-end; margin: 6px 0 22px; }
.mf-user div { background:#ECE7FF; color:#17142B; border-radius:22px; padding:12px 18px; font-size:15px; max-width:75%; line-height:1.5; }
.mf-row { display:flex; gap:14px; align-items:flex-start; margin: 0 0 26px; }
.mf-av { width:32px; height:32px; border-radius:50%; background:#5B3FD6; color:#fff; font-weight:800; font-size:12px;
         display:flex; align-items:center; justify-content:center; flex:0 0 auto; }
.mf-body { font-size:15px; line-height:1.65; color:#17142B; min-width:0; }
.mf-warn { background:#FFF4D6; border:1px solid #F3D88E; border-radius:16px; padding:14px 16px; }
.mf-tag { font-size:12px; font-weight:800; letter-spacing:.06em; text-transform:uppercase; color:#7A5200; margin-bottom:4px; }
.mf-src { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:12px; }
.mf-chip { display:inline-flex; align-items:center; gap:6px; padding:7px 12px; border-radius:999px; background:#F1EEFF;
           border:1px solid #DAD5F2; font-size:13px; font-weight:600; color:#4A32C4 !important; text-decoration:none !important; }
.mf-chip:hover { border-color:#5B3FD6; }
.mf-date { font-size:12px; color:#615C7C; }

/* input bar */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background:#F7F6FF !important; }
[data-testid="stChatInput"] { background:#FFFFFF !important; border:1px solid #DAD5F2 !important; border-radius:28px !important;
        box-shadow:0 6px 24px rgba(91,63,214,0.12); }
[data-testid="stChatInput"] > div { background:transparent !important; border:none !important; }
[data-testid="stChatInput"] textarea { color:#17142B !important; font-size:16px !important; }
[data-testid="stChatInputSubmitButton"] { background:#5B3FD6 !important; border-radius:50% !important; }
[data-testid="stChatInputSubmitButton"] svg { fill:#FFFFFF !important; color:#FFFFFF !important; }
@media (max-width: 640px) {
  .mf-hero { padding: 12px 0 6px; } .mf-dots { margin-bottom: 12px; }
  .mf-hero h1 { font-size: 28px !important; } .mf-hero p { font-size: 14px; }
  .mf-pill { display: none; }
}
.mf-disc { text-align:center; font-size:12px; color:#615C7C; margin-top:-4px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_assistant():
    return Assistant()


bot = get_assistant()
if "history" not in st.session_state:
    st.session_state.history = []  # ("user", text) / ("bot", Reply)

# ---------- top bar ----------
left, right = st.columns([4, 1.2], vertical_alignment="center")
with left:
    st.markdown('<div class="mf-brand"><div class="mf-logo">mf</div><div class="mf-name">MF Facts</div>'
                '<div class="mf-pill">PPFAS Mutual Fund</div></div>', unsafe_allow_html=True)
with right:
    if st.button("New chat", key="newchat", icon=":material/add:", use_container_width=True):
        st.session_state.history = []
        st.rerun()


# ---------- rendering ----------
def render_user(text):
    st.markdown(f'<div class="mf-user"><div>{escape(text)}</div></div>', unsafe_allow_html=True)


def render_reply(r):
    chip = (f'<div class="mf-src"><a class="mf-chip" href="{escape(r.source_url)}" target="_blank" rel="noopener">'
            f'{escape(r.source_title)} ↗</a><span class="mf-date">Last updated from sources: {fmt_date(r.as_of)}</span></div>')
    if r.kind in REFUSAL_LABEL:
        body = (f'<div class="mf-warn"><div class="mf-tag">{REFUSAL_LABEL[r.kind]}</div>'
                f'{escape(r.text)}{chip}</div>')
    else:
        body = f"{escape(r.text)}{chip}"
    st.markdown(f'<div class="mf-row"><div class="mf-av">mf</div><div class="mf-body">{body}</div></div>',
                unsafe_allow_html=True)


clicked = None
if not st.session_state.history:
    st.markdown(
        """<div class="mf-hero">
        <div class="mf-dots" aria-hidden="true"><span style="background:#3D7BFF"></span><span style="background:#7C5CFF"></span><span style="background:#C25CF0"></span></div>
        <h1>What do you want to know<br>about your fund?</h1>
        <p>Straight facts from official PPFAS, AMFI and SEBI pages — always with the source.</p></div>""",
        unsafe_allow_html=True,
    )
    for row in (SUGGESTIONS[:2], SUGGESTIONS[2:]):
        cols = st.columns(2)
        for col, (icon, label, q) in zip(cols, row):
            if col.button(label, icon=icon, use_container_width=True, key=q):
                clicked = q
    st.markdown('<div class="mf-covers">Covers: <b>Flexi Cap</b> · <b>ELSS Tax Saver</b> · <b>Large Cap</b> · '
                '<b>Liquid</b></div>', unsafe_allow_html=True)
else:
    st.write("")
    for role, item in st.session_state.history:
        if role == "user":
            render_user(item)
        else:
            render_reply(item)

typed = st.chat_input("Ask about exit load, SIP, lock-in…")
question = typed or clicked
if question:
    reply = bot.ask(question)
    shown = "[message hidden — it contained personal details]" if reply.kind == "refusal_pii" else question
    st.session_state.history += [("user", shown), ("bot", reply)]
    st.rerun()  # redraw: hero gives way to the conversation

with getattr(st, "bottom", None) or st._bottom:
    st.markdown('<div class="mf-disc">Facts-only. No investment advice. Please don\'t share PAN, Aadhaar, '
                "OTPs, phone, email or account numbers.</div>", unsafe_allow_html=True)
