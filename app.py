import streamlit as st
import sqlite3
import re
import unicodedata
from pathlib import Path
from google import genai

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Ala Hazrat Digital Library",
    page_icon="📚",
    layout="centered"
)

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>
.main-title {
    text-align: center;
    font-size: 30px;
    font-weight: 700;
    margin-top: 20px;
}

.subtitle {
    text-align: center;
    color: #777;
    margin-bottom: 30px;
}

div[data-testid="stChatMessage"] {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# GEMINI
# =========================================================

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Gemini API Key পাওয়া যায়নি।")
    st.stop()

client = genai.Client(api_key=API_KEY)

MODEL = "gemini-3.6-flash"

# =========================================================
# DATABASE
# =========================================================

DB_FILE = Path("data/library.db")

if not DB_FILE.exists():
    st.error("লাইব্রেরি ডাটাবেস পাওয়া যায়নি।")
    st.stop()


def db_connect():
    return sqlite3.connect(
        f"file:{DB_FILE}?mode=ro",
        uri=True
    )


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    # Arabic tatweel
    text = text.replace("ـ", "")

    # Arabic harakat
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    # Bengali punctuation
    punctuation = [
        "।", ",", "،", ";", "؛", ":",
        "?", "!", "(", ")", "[", "]",
        "{", "}", '"', "'"
    ]

    for p in punctuation:
        text = text.replace(p, " ")

    return text.lower()


# =========================================================
# GEMINI SEARCH TERM GENERATOR
# =========================================================

def create_search_terms(question):

    prompt = f"""
আপনি একটি ইসলামিক ডিজিটাল লাইব্রেরির Search Engine-এর সহকারী।

ব্যবহারকারীর প্রশ্ন:
{question}

এই প্রশ্নটি বুঝে এমন ১০-১৫টি গুরুত্বপূর্ণ অনুসন্ধান-শব্দ তৈরি করুন,
যেগুলো একটি ইসলামিক কিতাবের PDF-এ থাকতে পারে।

বিশেষভাবে:

- বাংলা প্রশ্ন হলে তার গুরুত্বপূর্ণ আরবি শব্দ দিন।
- প্রয়োজন হলে উর্দু শব্দ দিন।
- আলেম, ব্যক্তি, কিতাব, বিষয় বা পরিভাষার সম্ভাব্য বানান দিন।
- আরবি শব্দের বিভিন্ন প্রচলিত বানান বিবেচনা করুন।
- অপ্রয়োজনীয় সাধারণ শব্দ দেবেন না।

শুধু search terms দিন।
প্রতিটি term নতুন লাইনে লিখুন।
কোনো ব্যাখ্যা দেবেন না।

উদাহরণ:

احمد رضا خان
اعلی حضرت
امام احمد رضا
رضا خان
اعلی حضرت بریلوی
تصوف
شریعت
طریقت
"""

    try:

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        text = response.text.strip()

        terms = []

        for line in text.splitlines():

            line = line.strip()

            line = re.sub(
                r"^[\-\*\d\.\)\s]+",
                "",
                line
            )

            if line and len(line) >= 2:
                terms.append(line)

        # Original question-ও রাখি
        terms.append(question)

        # duplicate বাদ
        final_terms = []

        for term in terms:

            if term not in final_terms:
                final_terms.append(term)

        return final_terms[:20]

    except Exception:

        return [question]


# =========================================================
# DATABASE SEARCH
# =========================================================

def search_database(terms, limit=20):

    conn = db_connect()

    found = {}

    # -----------------------------------------------------
    # প্রতিটি search term দিয়ে LIKE search
    # -----------------------------------------------------

    for term in terms:

        words = re.findall(
            r"[\u0980-\u09FF\u0600-\u06FFa-zA-Z0-9]+",
            normalize(term)
        )

        for word in words:

            if len(word) < 2:
                continue

            try:

                cursor = conn.execute(
                    """
                    SELECT
                        book,
                        pdf_page,
                        text
                    FROM pages
                    WHERE search_text LIKE ?
                    LIMIT 15
                    """,
                    (f"%{word}%",)
                )

                rows = cursor.fetchall()

                for book, page, text in rows:

                    key = (book, page)

                    if key not in found:

                        found[key] = {
                            "book": book,
                            "page": page,
                            "text": text,
                            "score": 0
                        }

                    found[key]["score"] += 1

            except Exception:
                pass

    conn.close()

    # -----------------------------------------------------
    # score অনুযায়ী সাজানো
    # -----------------------------------------------------

    results = list(found.values())

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:limit]


# =========================================================
# GEMINI ANSWER
# =========================================================

def answer_from_books(question, results):

    if not results:
        return None

    source_blocks = []

    for item in results:

        text = item["text"].strip()

        # অত্যন্ত বড় page হলে সীমিত করা
        if len(text) > 10000:
            text = text[:10000]

        source_blocks.append(
            f"""
==============================
কিতাবের নাম: {item["book"]}
PDF পৃষ্ঠা: {item["page"]}
==============================

{text}
"""
        )

    sources = "\n\n".join(source_blocks)

    prompt = f"""
আপনি "আলা হযরত ডিজিটাল লাইব্রেরি"-এর একজন গবেষণা সহকারী।

ব্যবহারকারীর প্রশ্ন:

{question}

নিচে লাইব্রেরিতে সংরক্ষিত PDF কিতাব থেকে পাওয়া সম্ভাব্য
প্রাসঙ্গিক পৃষ্ঠার লেখা দেওয়া হলো।

আপনার কাজ হলো শুধুমাত্র এই SOURCE MATERIAL-এর ভিত্তিতে উত্তর দেওয়া।

SOURCE MATERIAL:

{sources}

==================================================
কঠোর নিয়ম
==================================================

১. SOURCE MATERIAL-এর বাইরে থেকে কোনো তথ্যকে কিতাবের বক্তব্য
হিসেবে লিখবেন না।

২. কোনো উদ্ধৃতি বানাবেন না।

৩. কোনো কিতাবের নাম বা পৃষ্ঠা নম্বর অনুমান করবেন না।

৪. প্রশ্নের উত্তর SOURCE MATERIAL-এ থাকলে পরিষ্কারভাবে উত্তর দিন।

৫. গুরুত্বপূর্ণ হলে মূল আরবি ইবারত হুবহু দিন।

৬. আরবি ইবারতের পরে বাংলা অনুবাদ দিন।

৭. রেফারেন্সের ক্ষেত্রে এই ফরম্যাট ব্যবহার করুন:

📚 কিতাব: [কিতাবের নাম]
📄 PDF পৃষ্ঠা: [পৃষ্ঠা নম্বর]

৮. একাধিক কিতাব বা পৃষ্ঠা থেকে তথ্য পাওয়া গেলে প্রত্যেকটির
রেফারেন্স আলাদাভাবে দিন।

৯. SOURCE MATERIAL যথেষ্ট না হলে বলুন:

"সংরক্ষিত কিতাবের পাওয়া অংশে এই প্রশ্নের পর্যাপ্ত তথ্য পাওয়া যায়নি।"

১০. নিজের সাধারণ জ্ঞান দিয়ে শূন্যস্থান পূরণ করবেন না।

১১. ইসলামিক বিষয়ে মতামত দেওয়ার সময় SOURCE MATERIAL-এর বক্তব্যকে
প্রাধান্য দিন।

১২. উত্তর বাংলা ভাষায় দিন।

এখন প্রশ্নটির উত্তর দিন।
"""

    try:

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        return response.text

    except Exception as e:

        return "AI উত্তর দিতে সমস্যা হয়েছে।"


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">📚 আলা হযরত ডিজিটাল লাইব্রেরি</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">সংরক্ষিত কিতাবসমূহ থেকে জিজ্ঞাসা করুন</div>',
    unsafe_allow_html=True
)

# =========================================================
# CHAT HISTORY
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =========================================================
# CHAT INPUT
# =========================================================

question = st.chat_input(
    "আপনার ইসলামিক প্রশ্ন লিখুন..."
)


# =========================================================
# QUESTION PROCESSING
# =========================================================

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("কিতাবসমূহ থেকে তথ্য খোঁজা হচ্ছে..."):

            # ১. বাংলা প্রশ্ন থেকে search terms
            search_terms = create_search_terms(question)

            # ২. database search
            results = search_database(
                search_terms,
                limit=20
            )

            # ৩. AI answer
            if results:

                answer = answer_from_books(
                    question,
                    results
                )

            else:

                answer = (
                    "দুঃখিত, সংরক্ষিত কিতাবসমূহে "
                    "এই প্রশ্নের সঙ্গে সম্পর্কিত "
                    "নির্ভরযোগ্য তথ্য পাওয়া যায়নি।"
                )

            st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
