import streamlit as st
import sqlite3
import re
import unicodedata
from pathlib import Path
from google import genai
from google.genai import types


# =========================================================
# SETTINGS
# =========================================================

DB_FILE = Path("data/library.db")


st.set_page_config(
    page_title="আলা হযরত AI",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# =========================================================
# GEMINI API KEY
# =========================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = ""

if not GEMINI_API_KEY:
    st.error("Gemini API Key পাওয়া যায়নি। Streamlit Secrets পরীক্ষা করুন।")
    st.stop()


# =========================================================
# SIMPLE DESIGN
# =========================================================

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        display: none;
    }

    .block-container {
        max-width: 850px;
        padding-top: 35px;
        padding-bottom: 100px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HEADER
# =========================================================

st.title("📚 আলা হযরত AI")

st.caption("কিতাবভিত্তিক ইসলামিক গবেষণা সহকারী")


# =========================================================
# DATABASE
# =========================================================

@st.cache_resource
def get_database():

    if not DB_FILE.exists():
        return None

    return sqlite3.connect(
        f"file:{DB_FILE}?mode=ro",
        uri=True,
        check_same_thread=False
    )


# =========================================================
# NORMALIZE TEXT
# =========================================================

def normalize_text(text):

    text = unicodedata.normalize("NFKC", text)

    text = text.replace("ـ", "")

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    return text.lower().strip()


# =========================================================
# GET TOKENS
# =========================================================

def get_tokens(text):

    text = normalize_text(text)

    tokens = re.findall(
        r"[\u0980-\u09FF\u0600-\u06FFA-Za-z0-9]+",
        text
    )

    stopwords = {
        "কি", "কী", "কেন", "কিভাবে", "কীভাবে",
        "এর", "এবং", "ও", "এই", "সে", "যে",
        "থেকে", "জন্য", "সম্পর্কে", "বলুন",
        "বলেন", "হয়", "হয়", "আছে", "ছিল",
        "হবে", "করা", "করুন", "একটি", "একজন",

        "ما", "هو", "في", "من", "عن",
        "هل", "و", "يا", "قال"
    }

    tokens = [
        token
        for token in tokens
        if len(token) > 1
        and token not in stopwords
    ]

    return tokens


# =========================================================
# SEARCH DATABASE
# =========================================================

def search_library(question, limit=12):

    conn = get_database()

    if conn is None:
        return []

    tokens = get_tokens(question)

    if not tokens:
        return []


    # -----------------------------------------------------
    # FTS SEARCH
    # -----------------------------------------------------

    try:

        query = " OR ".join(
            '"' + token.replace('"', '') + '"'
            for token in tokens[:15]
        )

        cursor = conn.execute(
            """
            SELECT rowid
            FROM pages_fts
            WHERE pages_fts MATCH ?
            ORDER BY bm25(pages_fts)
            LIMIT ?
            """,
            (query, limit)
        )

        ids = [
            row[0]
            for row in cursor.fetchall()
        ]

        if ids:

            placeholders = ",".join(
                "?" for _ in ids
            )

            cursor = conn.execute(
                f"""
                SELECT
                    id,
                    book,
                    pdf_page,
                    text
                FROM pages
                WHERE id IN ({placeholders})
                """,
                ids
            )

            rows = cursor.fetchall()

            row_map = {
                row[0]: row
                for row in rows
            }

            results = [
                row_map[i]
                for i in ids
                if i in row_map
            ]

            if results:
                return results

    except Exception:
        pass


    # -----------------------------------------------------
    # NORMAL LIKE SEARCH
    # -----------------------------------------------------

    results = []

    for token in tokens[:10]:

        try:

            cursor = conn.execute(
                """
                SELECT
                    id,
                    book,
                    pdf_page,
                    text
                FROM pages
                WHERE search_text LIKE ?
                LIMIT ?
                """,
                (
                    "%" + token + "%",
                    limit
                )
            )

            rows = cursor.fetchall()

            for row in rows:

                if row not in results:
                    results.append(row)

                if len(results) >= limit:
                    break

        except Exception:
            continue

        if len(results) >= limit:
            break


    return results[:limit]


# =========================================================
# GEMINI CLIENT
# =========================================================

@st.cache_resource
def get_gemini_client():

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# ASK GEMINI
# =========================================================

def ask_gemini(question, results):

    if not results:

        return (
            "দুঃখিত, লাইব্রেরিতে সংরক্ষিত "
            "কিতাবসমূহে এই বিষয়ে নির্ভরযোগ্য "
            "তথ্য পাওয়া যায়নি।"
        )


    context_parts = []


    for row in results:

        book = row[1]
        page = row[2]
        text = row[3]

        text = text[:9000]

        context_parts.append(
            f"""
===============================
কিতাব: {book}
PDF পৃষ্ঠা: {page}
===============================

{text}
"""
        )


    context = "\n".join(context_parts)


    # =====================================================
    # AI INSTRUCTION
    # =====================================================

    instruction = """

আপনি "আলা হযরত AI" নামের একটি
কিতাবভিত্তিক ইসলামিক গবেষণা সহকারী।

আপনার উত্তর প্রদত্ত কিতাবের অংশের
ভিত্তিতে দিতে হবে।

কঠোর নিয়ম:

১। নিজের মনগড়া তথ্য দেবেন না।

২। কনটেক্সটে তথ্য না থাকলে উত্তর বানাবেন না।

৩। কোনো আরবি ইবারত বানাবেন না।

৪। কোনো হাদিস বানাবেন না।

৫। কোনো আলেমের বক্তব্য বানাবেন না।

৬। কোনো বইয়ের নাম বানাবেন না।

৭। কোনো পৃষ্ঠা নম্বর বানাবেন না।

৮। কনটেক্সটে থাকা বইয়ের নাম ও PDF
পৃষ্ঠা পরিবর্তন করবেন না।

৯। ব্যবহারকারী আরবি ইবারত চাইলে
কনটেক্সটে থাকা আরবি ইবারত ব্যবহার করুন।

১০। বাংলা অনুবাদ চাইলে অনুবাদ দিন।

১১। প্রয়োজন হলে আগে আরবি ইবারত,
তারপর বাংলা অনুবাদ ও ব্যাখ্যা দিন।

১২। শেষে রেফারেন্স দিন।

ফরম্যাট:

রেফারেন্স:
কিতাবের নাম — PDF পৃষ্ঠা

"""


    client = get_gemini_client()


    response = client.models.generate_content(

        model="gemini-3.6-flash",

        contents=f"""
লাইব্রেরি থেকে পাওয়া কিতাবের অংশ:

{context}


ব্যবহারকারীর প্রশ্ন:

{question}
""",

        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.1
        )
    )


    return response.text


# =========================================================
# CHAT MEMORY
# =========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# =========================================================
# FIRST PAGE
# =========================================================

if len(st.session_state.messages) == 0:

    st.write("")
    st.write("")
    st.write("")
    st.write("")

    st.markdown(
        "<h2 style='text-align:center;'>কী জানতে চান?</h2>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center;'>"
        "আপনার ইসলামিক প্রশ্ন লিখুন এবং "
        "আলা হযরত AI-কে জিজ্ঞাসা করুন।"
        "</p>",
        unsafe_allow_html=True
    )

    st.write("")
    st.write("")


# =========================================================
# SHOW CHAT
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )


# =========================================================
# INPUT
# =========================================================

prompt = st.chat_input(
    "আপনার প্রশ্ন লিখুন..."
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if prompt:

    # User message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):

        st.markdown(prompt)


    # AI answer
    with st.chat_message("assistant"):

        with st.spinner("কিতাবসমূহে খোঁজা হচ্ছে..."):

            try:

                results = search_library(
                    prompt,
                    limit=12
                )

                answer = ask_gemini(
                    prompt,
                    results
                )

            except Exception as e:

                answer = (
                    "দুঃখিত, উত্তর দিতে সমস্যা হয়েছে। "
                    "কিছুক্ষণ পর আবার চেষ্টা করুন।"
                )

        st.markdown(answer)


    # Save answer
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
