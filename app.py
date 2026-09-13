import streamlit as st
from pypdf import PdfReader
from google import genai
from pathlib import Path


# =========================================================
# Gemini API Key
# =========================================================
PART1 = "AQ.Ab8RN6JkpctopwsjL03-e5u"
PART2 = "UbWfrU6Irq0OjRg_v4043TUi6IA"

GEMINI_API_KEY = PART1 + PART2


# =========================================================
# Page Configuration
# =========================================================
st.set_page_config(
    page_title="আলা হযরত ডিজিটাল লাইব্রেরি",
    page_icon="📚",
    layout="wide"
)


# =========================================================
# CSS
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
    color: white;
    font-size: 28px;
}

.main-header p {
    margin-top: 8px;
    color: #e0f2f1;
}

.book-box {
    background-color: #f1f8f6;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 8px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# Header
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
# Books Folder
# =========================================================
BOOKS_FOLDER = Path("books")


# =========================================================
# PDF থেকে Text Extract
# =========================================================
@st.cache_data(show_spinner=False)
def load_books():

    all_text = ""
    book_names = []
    total_pages = 0

    # books folder না থাকলে
    if not BOOKS_FOLDER.exists():
        BOOKS_FOLDER.mkdir(parents=True, exist_ok=True)
        return "", [], 0

    # সব PDF খুঁজে বের করা
    pdf_files = sorted(BOOKS_FOLDER.glob("*.pdf"))

    for pdf_file in pdf_files:

        try:

            reader = PdfReader(str(pdf_file))

            book_names.append(pdf_file.name)

            # সম্পূর্ণ PDF পড়বে
            for page_number, page in enumerate(reader.pages, start=1):

                try:
                    text = page.extract_text()
                except Exception:
                    text = None

                if text and text.strip():

                    all_text += (
                        "\n\n"
                        "==================================================\n"
                        f"কিতাব: {pdf_file.name}\n"
                        f"PDF পৃষ্ঠা: {page_number}\n"
                        "==================================================\n"
                        f"{text}\n"
                    )

                    total_pages += 1

        except Exception as e:

            all_text += (
                f"\nকিতাব পড়তে সমস্যা হয়েছে: "
                f"{pdf_file.name}\n"
                f"Error: {e}\n"
            )

    return all_text, book_names, total_pages


# =========================================================
# কিতাব Load
# =========================================================
with st.spinner("📚 লাইব্রেরির কিতাব প্রস্তুত করা হচ্ছে..."):

    pdf_texts, book_names, total_pages = load_books()


# =========================================================
# Sidebar
# =========================================================
st.sidebar.title("📖 ডিজিটাল লাইব্রেরি")

if book_names:

    st.sidebar.success(
        f"📚 মোট {len(book_names)}টি কিতাব"
    )

    st.sidebar.markdown("### 📚 যুক্তকৃত কিতাব")

    for book in book_names:
        st.sidebar.write(f"📕 {book}")

    st.sidebar.markdown("---")

    st.sidebar.write(
        f"📄 Text পাওয়া পৃষ্ঠা: {total_pages}"
    )

else:

    st.sidebar.warning(
        "⚠️ books folder-এ কোনো PDF পাওয়া যায়নি।"
    )


# =========================================================
# Question Section
# =========================================================
st.markdown("### 💬 কিতাব থেকে প্রশ্ন করুন")

st.info(
    "📚 এখানে প্রশ্ন করলে লাইব্রেরিতে সংরক্ষিত কিতাবসমূহ "
    "থেকে তথ্য অনুসন্ধান করে উত্তর দেওয়ার চেষ্টা করা হবে।"
)


# =========================================================
# Chat History
# =========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# =========================================================
# User Question
# =========================================================
if prompt := st.chat_input("আপনার প্রশ্ন লিখুন..."):

    # কিতাব না থাকলে
    if not pdf_texts:

        st.error(
            "⚠️ বর্তমানে লাইব্রেরিতে কোনো কিতাবের "
            "Text পাওয়া যাচ্ছে না।"
        )

        st.stop()


    # User message save
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    # User message show
    with st.chat_message("user"):

        st.markdown(prompt)


    # =====================================================
    # AI Answer
    # =====================================================
    with st.chat_message("assistant"):

        with st.spinner("🔎 কিতাবে অনুসন্ধান করে উত্তর প্রস্তুত করা হচ্ছে..."):

            try:

                # Gemini Client
                client = genai.Client(
                    api_key=GEMINI_API_KEY
                )


                # =================================================
                # Context
                # =================================================
                # আপাতত 150000 character ব্যবহার করা হচ্ছে
                context = pdf_texts[:150000]


                # =================================================
                # Instruction
                # =================================================
                system_instruction = f"""
আপনি "আলা হযরত ডিজিটাল লাইব্রেরি"-এর
একজন বিশ্বস্ত কিতাবভিত্তিক গবেষণা সহকারী।

আপনার কাছে যে কনটেক্সট দেওয়া হয়েছে,
তা GitHub-এর books folder-এ সংরক্ষিত PDF কিতাব
থেকে সংগ্রহ করা হয়েছে।

আপনাকে অবশ্যই নিচের নিয়মগুলো কঠোরভাবে অনুসরণ করতে হবে:

১। কেবল প্রদত্ত কিতাবের কনটেক্সটের ভিত্তিতে
উত্তর প্রদান করবেন।

২। কনটেক্সটে উত্তর না থাকলে নিজের সাধারণ জ্ঞান
ব্যবহার করে উত্তর তৈরি করবেন না।

৩। কোনো আরবি ইবারত, হাদিস, ফতোয়া বা উদ্ধৃতি
নিজে থেকে বানিয়ে লিখবেন না।

৪। কোনো রেফারেন্স বা পৃষ্ঠা নম্বর অনুমান করবেন না।

৫। কনটেক্সটে যে কিতাবের নাম এবং PDF পৃষ্ঠা
দেওয়া আছে, সেটিই রেফারেন্স হিসেবে ব্যবহার করবেন।

৬। ব্যবহারকারী যদি আরবি ইবারত চান,
তাহলে কনটেক্সটে থাকা আরবি ইবারতই প্রদান করবেন।

৭। আরবি ইবারতের সঙ্গে বাংলা অনুবাদ প্রয়োজন হলে
তার বাংলা অনুবাদ প্রদান করবেন।

৮। একই বিষয়ে একাধিক কিতাবে তথ্য থাকলে
প্রাসঙ্গিক একাধিক রেফারেন্স উল্লেখ করবেন।

৯। উত্তর পরিষ্কার, সংক্ষিপ্ত এবং গবেষণামূলক হবে।

১০। উত্তর শেষে "রেফারেন্স" শিরোনামে
কিতাবের নাম ও PDF পৃষ্ঠা উল্লেখ করবেন।

১১। যদি প্রদত্ত কনটেক্সটে প্রশ্নের উত্তর পাওয়া না যায়,
তাহলে বলবেন:

"দুঃখিত, লাইব্রেরিতে সংরক্ষিত কিতাবসমূহে
এই বিষয়ে কোনো তথ্য পাওয়া যায়নি।"

১২। কোনো তথ্য অনুমান করা সম্পূর্ণ নিষিদ্ধ।

--------------------------------------------------

কিতাবের কনটেক্সট:

{context}

--------------------------------------------------
"""


                # =================================================
                # Gemini API
                # =================================================
                response = client.models.generate_content(

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
                    "ত্রুটির বিবরণ:\n"
                    f"{e}"
                )


            # Show answer
            st.markdown(answer)


            # Save answer
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )
