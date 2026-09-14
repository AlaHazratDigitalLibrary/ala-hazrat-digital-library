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
</style>
""", unsafe_allow_html=True)

# =========================================================
# GEMINI
# =========================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Gemini API Key পাওয়া যাচ্ছে না। Streamlit Secrets পরীক্ষা করুন।")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.6-flash"

# =========================================================
# DATABASE
# =========================================================

DB_FILE = Path("data/library.db")

if not DB_FILE.exists():
    st.error("লাইব্রেরি ডাটাবেস পাওয়া যায়নি।")
    st.stop()


def get_connection():
    return sqlite3.connect(
        f"file:{DB_FILE}?mode=ro",
        uri=True
    )


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    # Arabic tatweel
    text = text.replace("ـ", "")

    # Arabic harakat
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)

    # Bengali punctuation / common punctuation
    text = text.replace("।", " ")
    text = text.replace(",", " ")
    text = text.replace("،", " ")
    text = text.replace(";", " ")
    text = text.replace("؛", " ")
    text = text.replace(":", " ")
    text = text.replace("ঃ", " ")

    return text.lower()


# =========================================================
# SEARCH WORDS
# =========================================================

def get_search_words(question):

    normalized = normalize_text(question)

    # শুধু meaningful শব্দ
    words = re.findall(
        r"[\u0980-\u09FF\u0600-\u06FFa-zA-Z0-9]+",
        normalized
    )

    # খুব ছোট সাধারণ শব্দ বাদ
    stop_words = {
        "কি",
        "কী",
        "কে",
        "কেন",
        "কোন",
        "কোনটি",
        "এর",
        "এবং",
        "ও",
        "বা",
        "যে",
        "এই",
        "সেই",
        "তে",
        "থেকে",
        "সম্পর্কে",
        "বিষয়ে",
        "বিষয়",
        "the",
        "what",
        "who",
        "why",
        "how",
        "is",
        "are",
        "of",
        "and"
    }

    words = [
        word for word in words
        if word not in stop_words and len(word) >= 2
    ]

    return words


# =========================================================
# SEARCH DATABASE
# =========================================================

def search_library(question, limit=12):

    words = get_search_words(question)

    if not words:
        return []

    conn = get_connection()
    results = []

    # -----------------------------------------------------
    # 1. FTS SEARCH
    # -----------------------------------------------------

    try:
        # OR search
        fts_query = " OR ".join(
            '"' + word.replace('"', '""') + '"'
            for word in words
        )

        cursor = conn.execute(
            """
            SELECT
                p.book,
                p.pdf_page,
                p.text
            FROM pages_fts f
            JOIN pages p
                ON p.id = f.rowid
            WHERE pages_fts MATCH ?
            LIMIT ?
            """,
            (fts_query, limit)
        )

        results = cursor.fetchall()

    except Exception:
        results = []

    # -----------------------------------------------------
    # 2. LIKE FALLBACK
    # -----------------------------------------------------

    if len(results) < 5:

        existing = {
            (row[0], row[1])
            for row in results
        }

        for word in words:

            try:
                cursor = conn.execute(
                    """
                    SELECT
                        book,
                        pdf_page,
                        text
                    FROM pages
                    WHERE search_text LIKE ?
                    LIMIT ?
                    """,
                    (f"%{word}%", limit)
                )

                for row in cursor.fetchall():

                    key = (row[0], row[1])

                    if key not in existing:
                        results.append(row)
                        existing.add(key)

                    if len(results) >= limit:
                        break

            except Exception:
                pass

            if len(results) >= limit:
                break

    conn.close()

    return results[:limit]


# =========================================================
# ANSWER GENERATION
# =========================================================

def generate_answer(question, results):

    if not results:
        return None

    context_parts = []

    for book, page, text in results:

        # খুব বড় page পাঠানো হবে না
        clean_text = text.strip()

        if len(clean_text) > 9000:
            clean_text = clean_text[:9000]

        context_parts.append(
            f"""
কিতাব: {book}
PDF পৃষ্ঠা: {page}

পাঠ:
{clean_text}
"""
        )

    context = "\n\n------------------------------\n\n".join(
        context_parts
    )

    prompt = f"""
আপনি "আলা হযরত ডিজিটাল লাইব্রেরি"-এর গবেষণা সহকারী।

ব্যবহারকারীর প্রশ্ন:
{question}

নিচে সংরক্ষিত কিতাবের PDF থেকে পাওয়া নির্দিষ্ট পৃষ্ঠার তথ্য দেওয়া হলো।

==============================
SOURCE MATERIAL
==============================

{context}

==============================
নির্দেশনা
==============================

১. শুধুমাত্র উপরের SOURCE MATERIAL-এর ভিত্তিতে উত্তর দিন।

২. SOURCE MATERIAL-এ উত্তর না থাকলে কোনো তথ্য নিজের থেকে বানাবেন না।

৩. কোনো কিতাব, পৃষ্ঠা, লেখক বা উদ্ধৃতি অনুমান করবেন না।

৪. উত্তর দেওয়ার সময় সংশ্লিষ্ট কিতাবের নাম এবং PDF পৃষ্ঠা নম্বর উল্লেখ করুন।

৫. SOURCE MATERIAL-এ আরবি ইবারত থাকলে প্রয়োজন অনুযায়ী মূল আরবি ইবারত দিন।

৬. ব্যবহারকারী যদি দলিল বা রেফারেন্স চান, তাহলে SOURCE MATERIAL-এর মধ্যেই থাকা তথ্য ব্যবহার করুন।

৭. একই বিষয়ের একাধিক পৃষ্ঠা থাকলে প্রয়োজন অনুযায়ী একাধিক রেফারেন্স দিন।

৮. উত্তর পরিষ্কার, সংক্ষিপ্ত এবং গবেষণামূলক বাংলা ভাষায় দিন।

৯. SOURCE MATERIAL-এর বাইরে কোনো তথ্যকে কিতাবের বক্তব্য হিসেবে উপস্থাপন করবেন না।

১০. যদি SOURCE MATERIAL যথেষ্ট না হয়, পরিষ্কারভাবে বলুন যে প্রদত্ত কিতাবের পাওয়া অংশে প্রশ্নটির পর্যাপ্ত তথ্য পাওয়া যায়নি।

প্রশ্নের উত্তর দিন।
"""

    try:

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text

    except Exception as e:

        return f"AI উত্তর দিতে সমস্যা হয়েছে: {e}"


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">📚 আলা হযরত ডিজিটাল লাইব্রেরি</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">সংরক্ষিত কিতাবসমূহ থেকে তথ্য অনুসন্ধান করুন</div>',
    unsafe_allow_html=True
)

# =========================================================
# SESSION
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# =========================================================
# OLD MESSAGES
# =========================================================

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
# PROCESS QUESTION
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

            results = search_library(
                question,
                limit=12
            )

            if not results:

                answer = (
                    "দুঃখিত, সংরক্ষিত কিতাবসমূহে "
                    "এই প্রশ্নের সঙ্গে সম্পর্কিত নির্ভরযোগ্য তথ্য "
                    "খুঁজে পাওয়া যায়নি।"
                )

            else:

                answer = generate_answer(
                    question,
                    results
                )

            st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
