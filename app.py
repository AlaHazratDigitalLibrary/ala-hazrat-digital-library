import streamlit as st
from pypdf import PdfReader
from google import genai

# =========================================================
# Gemini API Key
# =========================================================
PART1 = "AQ.Ab8RN6JkpctopwsjL03-e5u"
PART2 = "UbWfrU6Irq0OjRg_v4043TUi6IA"

GEMINI_API_KEY = PART1 + PART2


# =========================================================
# পেজ কনফিগারেশন
# =========================================================
st.set_page_config(
    page_title="আলা হযরত ডিজিটাল লাইব্রেরি",
    page_icon="📚",
    layout="wide"
)


# =========================================================
# CSS ডিজাইন
# =========================================================
st.markdown("""
    <style>

    .main-header {
        background-color: #075e54;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }

    .main-header h1 {
        margin: 0;
        color: #ffffff;
        font-size: 28px;
    }

    .main-header p {
        margin-top: 5px;
        color: #e0f2f1;
    }

    </style>
""", unsafe_allow_html=True)


# =========================================================
# হেডার
# =========================================================
st.markdown("""
    <div class="main-header">
        <h1>📚 আলা হযরত ডিজিটাল লাইব্রেরি ও এআই অ্যাসিস্ট্যান্ট</h1>
        <p>
            ইমাম আহলে সুন্নাত শাহ আহমদ রযা খান রহ.-এর
            কিতাবভিত্তিক গবেষণা ও ফতোয়া অনুসন্ধান
        </p>
    </div>
""", unsafe_allow_html=True)


# =========================================================
# সাইডবার
# =========================================================
st.sidebar.title("📖 কিতাব ব্যবস্থাপনা")

uploaded_files = st.sidebar.file_uploader(
    "📥 কিতাব আপলোড করুন (PDF):",
    type="pdf",
    accept_multiple_files=True
)


# =========================================================
# PDF থেকে Text Extract
# =========================================================
@st.cache_data(show_spinner=False)
def extract_pdf_text(files):

    extracted_text = ""
    book_names = []

    for file in files:

        book_names.append(file.name)

        reader = PdfReader(file)

        # বর্তমানে সর্বোচ্চ 150 পৃষ্ঠা
        max_pages = min(len(reader.pages), 150)

        for i in range(max_pages):

            page = reader.pages[i]

            try:
                text = page.extract_text()
            except Exception:
                text = None

            if text:

                extracted_text += (
                    f"\n\n"
                    f"--- [রেফারেন্স -> "
                    f"কিতাব: {file.name}, "
                    f"পৃষ্ঠা: {i + 1}] ---\n"
                    f"{text}"
                )

    return extracted_text, book_names


# =========================================================
# PDF প্রসেস
# =========================================================
pdf_texts = ""
book_names = []

if uploaded_files:

    with st.sidebar.status(
        "কিতাব প্রসেস হচ্ছে...",
        expanded=True
    ) as status:

        pdf_texts, book_names = extract_pdf_text(uploaded_files)

        status.update(
            label="কিতাব লোড সম্পন্ন!",
            state="complete",
            expanded=False
        )


# =========================================================
# কিতাবের তালিকা
# =========================================================
if book_names:

    st.sidebar.markdown("### 📚 যুক্তকৃত কিতাবের তালিকা:")

    for b_name in book_names:

        st.sidebar.write(
            f"• {b_name}"
        )


# =========================================================
# প্রশ্ন অংশ
# =========================================================
st.markdown("### 💬 কিতাব থেকে প্রশ্ন করুন")


# =========================================================
# Chat History
# =========================================================
if "messages" not in st.session_state:

    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )


# =========================================================
# User Question
# =========================================================
if prompt := st.chat_input("প্রশ্ন লিখুন..."):

    # PDF না থাকলে
    if not pdf_texts:

        st.warning(
            "⚠️ দয়া করে সাইডবার থেকে অন্তত একটি PDF কিতাব আপলোড করুন।"
        )

        st.stop()


    # User message সংরক্ষণ
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    # User message দেখানো
    with st.chat_message("user"):

        st.markdown(prompt)


    # =====================================================
    # AI Response
    # =====================================================
    with st.chat_message("assistant"):

        with st.spinner("উত্তর প্রস্তুত করা হচ্ছে..."):

            try:

                # Gemini Client
                client = genai.Client(
                    api_key=GEMINI_API_KEY
                )


                # বর্তমানে সর্বোচ্চ 150000 character
                context = pdf_texts[:150000]


                # =================================================
                # System Instruction
                # =================================================
                system_instruction = f"""
আপনি আলা হযরত ইমাম আহমদ রযা খান রহ.-এর
কিতাবসমূহের একজন প্রাজ্ঞ ও বিশ্বস্ত
কিতাবভিত্তিক গবেষণা সহকারী।

আপনার জন্য নিচের PDF কিতাবের Text প্রদান করা হয়েছে।

আপনাকে অবশ্যই নিচের নিয়মগুলো অনুসরণ করতে হবে:

১। কেবলমাত্র প্রদান করা কিতাবের কনটেক্সট অনুসরণ করে
ব্যবহারকারীর প্রশ্নের উত্তর দিন।

২। কনটেক্সটে তথ্য না থাকলে নিজের জ্ঞান থেকে
কোনো তথ্য যোগ করবেন না।

৩। কোনো আরবি ইবারত, হাদিস, ফতোয়া বা উদ্ধৃতি
নিজে থেকে বানিয়ে লিখবেন না।

৪। কোনো কিতাবের পৃষ্ঠা নম্বর অনুমান করবেন না।

৫। উত্তরের শেষে অবশ্যই কিতাবের নাম এবং
PDF-এর পৃষ্ঠা নম্বর উল্লেখ করার চেষ্টা করবেন।

৬। যদি প্রশ্নের উত্তর প্রদত্ত কিতাবে পাওয়া না যায়,
তাহলে হুবহু বলুন:

"দুঃখিত, আপনার আপলোডকৃত কিতাবে
এই বিষয়ে কোনো তথ্য পাওয়া যায়নি।"

৭। যদি কিতাবে একাধিক জায়গায় তথ্য থাকে,
তাহলে যতগুলো প্রাসঙ্গিক রেফারেন্স পাওয়া যায়
সেগুলো উল্লেখ করুন।

৮। ব্যবহারকারী যদি আরবি ইবারত চান,
তাহলে কনটেক্সটে থাকা ইবারতই ব্যবহার করুন।
নিজে থেকে আরবি বাক্য তৈরি করবেন না।

৯। উত্তর পরিষ্কার, গবেষণামূলক এবং
বাংলা ভাষায় প্রদান করুন।

১০। কিতাবের নাম, পৃষ্ঠা এবং উদ্ধৃতির ক্ষেত্রে
অনুমান করা সম্পূর্ণ নিষিদ্ধ।

--------------------------------------------------

কিতাবের কনটেক্সট:

{context}

--------------------------------------------------
"""


                # =================================================
                # Gemini API
                # =================================================
                response = client.models.generate_content(

                    # পুরোনো gemini-2.5-flash এর পরিবর্তে
                    # নতুন মডেল
                    model="gemini-3.6-flash",

                    contents=(
                        system_instruction
                        + "\n\n"
                        + "ব্যবহারকারীর প্রশ্ন:\n"
                        + prompt
                    )
                )


                # =================================================
                # Answer
                # =================================================
                answer = response.text


            except Exception as e:

                answer = (
                    "⚠️ উত্তর তৈরি করতে সমস্যা হয়েছে।\n\n"
                    f"ত্রুটির বিবরণ:\n{e}"
                )


            # Answer দেখানো
            st.markdown(answer)


            # Assistant message সংরক্ষণ
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )
