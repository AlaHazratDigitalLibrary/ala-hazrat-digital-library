import streamlit as st

# ==============================
# PAGE SETTINGS
# ==============================

st.set_page_config(
    page_title="আলা হযরত AI",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# CUSTOM CSS
# ==============================

st.markdown("""
<style>

    /* পুরো ওয়েবসাইট */
    .stApp {
        background: #ffffff;
    }

    /* Streamlit-এর উপরের অংশ */
    header {
        visibility: hidden;
    }

    /* Main menu */
    #MainMenu {
        visibility: hidden;
    }

    /* Footer */
    footer {
        visibility: hidden;
    }

    /* Sidebar সম্পূর্ণ বন্ধ */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* মূল অংশ */
    .block-container {
        max-width: 850px;
        padding-top: 25px;
        padding-bottom: 120px;
    }

    /* Logo / Title */
    .logo {
        text-align: center;
        margin-top: 10px;
        margin-bottom: 35px;
    }

    .logo-icon {
        font-size: 42px;
        margin-bottom: 5px;
    }

    .logo-title {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
    }

    .logo-subtitle {
        font-size: 14px;
        color: #777777;
        margin-top: 7px;
    }

    /* Welcome */
    .welcome {
        text-align: center;
        margin-top: 90px;
        margin-bottom: 30px;
    }

    .welcome h2 {
        font-size: 25px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .welcome p {
        color: #777777;
        font-size: 15px;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        max-width: 850px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Input box */
    [data-testid="stChatInput"] textarea {
        font-size: 16px;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
    }

    /* Mobile */
    @media (max-width: 600px) {

        .block-container {
            padding-left: 15px;
            padding-right: 15px;
            padding-top: 15px;
        }

        .logo-title {
            font-size: 23px;
        }

        .welcome {
            margin-top: 65px;
        }

        .welcome h2 {
            font-size: 21px;
        }

    }

</style>
""", unsafe_allow_html=True)

# ==============================
# HEADER
# ==============================

st.markdown("""
<div class="logo">

    <div class="logo-icon">📚</div>

    <div class="logo-title">
        আলা হযরত AI
    </div>

    <div class="logo-subtitle">
        কিতাবভিত্তিক ইসলামিক গবেষণা সহকারী
    </div>

</div>
""", unsafe_allow_html=True)

# ==============================
# WELCOME SCREEN
# ==============================

if "messages" not in st.session_state:
    st.session_state.messages = []

if len(st.session_state.messages) == 0:

    st.markdown("""
    <div class="welcome">

        <h2>কী জানতে চান?</h2>

        <p>
            আলা হযরতের কিতাবসমূহ থেকে আপনার প্রশ্ন করুন
        </p>

    </div>
    """, unsafe_allow_html=True)

# ==============================
# OLD MESSAGES
# ==============================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================
# QUESTION BOX
# ==============================

prompt = st.chat_input(
    "আপনার প্রশ্ন লিখুন..."
)

if prompt:

    # User message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Temporary answer
    with st.chat_message("assistant"):
        answer = "আপনার প্রশ্ন গ্রহণ করা হয়েছে।"

        st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
