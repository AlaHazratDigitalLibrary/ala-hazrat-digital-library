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
# CSS / DESIGN
# =========================================================

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

/* Main container */
.block-container {
    max-width: 900px !important;
    padding-top: 30px !important;
    padding-bottom: 110px !important;
    padding-left: 20px !important;
    padding-right: 20px !important;
}


/* Header */
.title {
    text-align: center;
    font-size: 32px;
    font-weight: 700;
    margin-top: 10px;
    line-height: 1.4;
}

.subtitle {
    text-align: center;
    color: #777;
    font-size: 15px;
    margin-top: 6px;
}


/* Welcome */
.welcome-box {
    min-height: 55vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 20px;
}

.welcome-icon {
    font-size: 52px;
    margin-bottom: 12px;
}

.welcome-title {
    font-size: 30px;
    font-weight: 600;
    margin-bottom: 10px;
}

.welcome-text {
    font-size: 16px;
    color: #777;
    max-width: 600px;
    line-height: 1.8;
}


/* Chat input */
[data-testid="stChatInput"] {
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
}


/* Mobile */
@media (max-width: 600px) {

    .block-container {
        padding-top: 20px !important;
        padding-left: 12px !important;
        padding-right: 12px !important;
    }

    .title {
        font-size: 25px;
    }

    .subtitle {
        font-size: 13px;
    }

    .welcome-box {
        min-height: 58vh;
    }

    .welcome-icon {
        font-size: 44px;
    }

    .welcome-title {
        font-size: 24px;
    }

    .welcome-text {
        font-size: 14px;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="title">📚 আলা হযরত AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">কিতাবভিত্তিক ইসলামিক গবেষণা সহকারী</div>',
    unsafe_allow_html=True
)


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
# NORMALIZE
# =========================================================

def normalize_text(text):

    text = unicodedata.normalize("NFKC", text)

    # Arabic Tatweel
    text = text.replace("ـ", "")

    # Arabic harakat
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    return text.lower().strip()


# =========================================================
# TOKENS
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
        "হবে", "করা", "করুন", "একটি",
        "একজন", "সম্পর্কে",

        "ما", "هو", "في", "من", "عن",
        "هل", "و", "يا", "قال",
        "هذه", "هذا", "ذلك",
        "التي", "الذي"
    }

    return [
        token
        for token in tokens
        if len(token) > 1
        and token not in stopwords
    ]


# =========================================================
# LIBRARY SEARCH
# =========================================================

def search_library(question, limit=12):

    conn = get_database()

    if conn is None:
        return []

    tokens = get_tokens(question)

    if not tokens:
        return []


    # =====================================================
    # 1. FTS AND SEARCH
    # =====================================================

    results = []

    and_query = " AND ".join(
        '"' + token.replace('"', '') + '"'
        for token in tokens[:10]
    )

    try:

        cursor = conn.execute(
            """
            SELECT rowid
            FROM pages_fts
            WHERE pages_fts MATCH ?
            ORDER BY bm25(pages_fts)
            LIMIT ?
            """,
            (and_query, limit)
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

            data = cursor.fetchall()

            data_dict = {
                row[0]: row
                for row in data
            }

            results = [
                data_dict[i]
                for i in ids
                if i in data_dict
            ]

    except Exception:
        results = []


    # =====================================================
    # 2. FTS OR SEARCH
    # =====================================================

    if not results:

        or_query = " OR ".join(
            '"' + token.replace('"', '') + '"'
            for token in tokens[:15]
        )

        try:

            cursor = conn.execute(
                """
                SELECT rowid
                FROM pages_fts
                WHERE pages_fts MATCH ?
                ORDER BY bm25(pages_fts)
                LIMIT ?
                """,
                (or_query, limit)
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

                data = cursor.fetchall()

                data_dict = {
                    row[0]: row
                    for row in data
                }

                results = [
                    data_dict[i]
                    for i in ids
                    if i in data_dict
                ]

        except Exception:
            results = []


    # =====================================================
    # 3. LIKE FALLBACK
    # =====================================================
    # FTS কাজ না করলেও সাধারণ SQLite search করবে।

    if not results:

        for token in tokens[:8]:

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

def ask_gemini(question, search_results):

    if not search_results:

        return (
            "দুঃখিত, লাইব্রেরিতে সংরক্ষিত "
            "কিতাবসমূহে এই বিষয়ে নির্ভরযোগ্য "
            "তথ্য পাওয়া যায়নি।"
        )


    # =====================================================
    # BUILD CONTEXT
    # =====================================================

    context_parts = []

    for row in search_results:

        book = row[1]
        pdf_page = row[2]
        text = row[3]

        # প্রতি পৃষ্ঠা থেকে সর্বোচ্চ ৯০০০ অক্ষর
        text = text[:9000]

        context_parts.append(
            f"""
==================================================
কিতাবের নাম: {book}
PDF পৃষ্ঠা: {pdf_page}
==================================================

{text}

"""
        )

    context = "\n".join(context_parts)


    # =====================================================
    # SYSTEM INSTRUCTION
    # =====================================================

    system_instruction = """

আপনি "আলা হযরত AI" নামের একটি
কিতাবভিত্তিক ইসলামিক গবেষণা সহকারী।

আপনাকে লাইব্রেরির PDF থেকে প্রাসঙ্গিক
কিতাবের অংশ দেওয়া হয়েছে।

আপনার কাজ হলো সেই কিতাবের অংশের
ভিত্তিতে ব্যবহারকারীর প্রশ্নের উত্তর দেওয়া।

অত্যন্ত গুরুত্বপূর্ণ:

১। কনটেক্সটে তথ্য থাকলে তার ভিত্তিতেই উত্তর দিন।

২। কনটেক্সটে তথ্য না থাকলে নিজের সাধারণ
জ্ঞান দিয়ে উত্তর বানাবেন না।

৩। কোনো আরবি ইবারত বানাবেন না।

৪। কোনো হাদিস বানাবেন না।

৫। কোনো আলেমের বক্তব্য বানাবেন না।

৬। কোনো বইয়ের নাম বানাবেন না।

৭। কোনো পৃষ্ঠা নম্বর বানাবেন না।

৮। PDF পৃষ্ঠা পরিবর্তন করবেন না।

৯। ব্যবহারকারী আরবি ইবারত চাইলে,
কনটেক্সটে থাকা আরবি ইবারত ব্যবহার করবেন।

১০। ব্যবহারকারী বাংলা অনুবাদ চাইলে,
আরবি ইবারতের বাংলা অনুবাদ দিন।

১১। সম্ভব হলে উত্তর এভাবে সাজান:

আরবি ইবারত:
[কনটেক্সটে থাকা ইবারত]

বাংলা অনুবাদ:
[অনুবাদ]

ব্যাখ্যা:
[প্রাসঙ্গিক ব্যাখ্যা]

রেফারেন্স:
[কিতাবের নাম] — PDF পৃষ্ঠা [নম্বর]

১২। একাধিক কিতাবে তথ্য পাওয়া গেলে
একাধিক রেফারেন্স দিতে পারেন।

১৩। কনটেক্সটে কোনো তথ্য না থাকলে
স্পষ্টভাবে বলবেন:

"দুঃখিত, লাইব্রেরিতে সংরক্ষিত
কিতাবসমূহে এই বিষয়ে নির্ভরযোগ্য
তথ্য পাওয়া যায়নি।"

১৪। কোনো কাল্পনিক রেফারেন্স তৈরি করবেন না।

১৫। PDF পৃষ্ঠা এবং মূল মুদ্রিত কিতাবের
পৃষ্ঠা একই বিষয় নয়। তাই কেবল
"PDF পৃষ্ঠা" হিসেবে উল্লেখ করবেন।

"""


    # =====================================================
    # GEMINI
    # =====================================================

    client = get_gemini_client()

    response = client.models.generate_content(

        model="gemini-3.6-flash",

        contents=f"""

লাইব্রেরি থেকে পাওয়া কিতাবের অংশ:

{context}


==================================================

ব্যবহারকারীর প্রশ্ন:

{question}

""",

        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
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
# WELCOME SCREEN
# =========================================================

if len(st.session_state.messages) == 0:

    st.markdown(
        """
        <div class="welcome-box">

            <div class="welcome-icon">
                📖
            </div>

            <div class="welcome-title">
                কী জানতে চান?
            </div>

            <div class="welcome-text">
                আপনার ইসলামিক প্রশ্ন লিখুন।
                আলা হযরত AI সংরক্ষিত কিতাবসমূহ
                থেকে তথ্য খুঁজে উত্তর দেওয়ার চেষ্টা করবে।
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

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
# PROCESS
# =========================================================

if prompt:

    # User
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):

        st.markdown(prompt)


    # Assistant
    with st.chat_message("assistant"):

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
                "দুঃখিত, বর্তমানে একটি প্রযুক্তিগত "
                "সমস্যা হয়েছে। কিছুক্ষণ পর আবার চেষ্টা করুন।"
            )

        st.markdown(answer)


    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
