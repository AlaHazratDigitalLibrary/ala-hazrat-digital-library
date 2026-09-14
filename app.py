import streamlit as st

st.set_page_config(
    page_title="আলা হযরত AI",
    page_icon="📚",
    layout="centered"
)

st.markdown("""
<style>
#MainMenu {
    visibility: hidden;
}

header {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

[data-testid="stSidebar"] {
    display: none;
}

.block-container {
    max-width: 850px;
    padding-top: 40px;
}

.title {
    text-align: center;
    font-size: 30px;
    font-weight: bold;
    margin-top: 20px;
}

.subtitle {
    text-align: center;
    color: #777;
    margin-top: 8px;
}

.welcome {
    text-align: center;
    margin-top: 120px;
}

.welcome h2 {
    font-size: 26px;
}

.welcome p {
    color: #777;
}

</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="title">📚 আলা হযরত AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">কিতাবভিত্তিক ইসলামিক গবেষণা সহকারী</div>',
    unsafe_allow_html=True
)


st.markdown("""
<div class="welcome">
    <h2>কী জানতে চান?</h2>
    <p>আপনার প্রশ্ন লিখুন এবং আলা হযরত AI-কে জিজ্ঞাসা করুন।</p>
</div>
""", unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


prompt = st.chat_input("আপনার প্রশ্ন লিখুন...")


if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        st.markdown("আপনার প্রশ্ন গ্রহণ করা হয়েছে।")
