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
# DESIGN
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

.block-container {
    max-width: 850px;
    padding-top: 35px;
    padding-bottom: 100px;
}

.title {
    text-align: center;
    font-size: 30px;
    font-weight: 700;
    margin-top: 10px;
}

.subtitle {
    text-align: center;
    color: #777;
    margin-top: 8px;
    font-size: 14px;
}

.welcome {
    text-align: center;
    margin-top: 115px;
    margin-bottom: 35px;
}

.welcome h2 {
    font-size: 26px;
    font-weight: 600;
}

.welcome p {
    color: #777;
    font-size: 15px;
}

[data-testid="stChatInput"] {
    max-width: 850px;
    margin-left: auto;
    margin-right: auto;
}

@media (max-width: 600px) {

    .block-container {
        padding-left: 15px;
        padding-right: 15px;
        padding-top: 25px;
    }

    .title {
        font-size: 24px;
    }

    .welcome {
        margin-top: 70px;
    }

    .welcome h2 {
        font-size: 22px;
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
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):

    text = unicodedata.normalize("NFKC", text)

    # Arabic Tatweel
    text = text.replace("ـ", "")

    # Arabic Harakat
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    return text.lower()


# =========================================================
# QUESTION TOKENS
# =========================================================

def get_tokens(text):

    text = normalize_text(text)

    tokens = re.findall(
        r"[\u0980-\u09FF\u0600-\u06FFA-Za-z0-9]+",
        text
    )

    stopwords = {

        # Bengali
        "কি",
        "কী",
        "কেন",
        "কিভাবে",
        "কীভাবে",
        "এর",
        "এবং",
        "ও",
        "এই",
        "সে",
        "যে",
        "থেকে",
        "জন্য",
        "সম্পর্কে",
        "বলুন",
        "বলেন",
        "হয়",
        "হয়",
        "আছে",
        "ছিল",
        "হবে",
        "করা",
        "করুন",
        "একটি",
        "একজন",

        # Arabic
        "ما",
        "هو",
        "في",
        "من",
        "عن",
        "هل",
        "و",
        "يا",
        "قال",
        "هذه",
        "هذا",
        "ذلك",
        "التي",
        "الذي"
    }

    tokens = [
        token
        for token in tokens
        if len(token) > 1
        and token not in stopwords
    ]

    return tokens


# =========================================================
# SEARCH LIBRARY
# =========================================================

def search_library(question, limit=12):

    conn = get_database()

    if conn is None:
        return []

    tokens = get_tokens(question)

    if not tokens:
        return []


    # -----------------------------------------------------
    # প্রথমে AND Search
    # -----------------------------------------------------

    and_query = " AND ".join(
        '"' + token.replace('"', '') + '"'
        for token in tokens[:12]
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
            (
                and_query,
                limit
            )
        )

        ids = [
            row[0]
            for row in cursor.fetchall()
        ]

    except Exception:

        ids = []


    # -----------------------------------------------------
    # AND না পেলে OR Search
    # -----------------------------------------------------

    if not ids:

        or_query = " OR ".join(
            '"' + token.replace('"', '') + '"'
            for token in tokens[:18]
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
                (
                    or_query,
                    limit
                )
            )

            ids = [
                row[0]
                for row in cursor.fetchall()
            ]

        except Exception:

            ids = []


    if not ids:
        return []


    # -----------------------------------------------------
    # Database থেকে সম্পূর্ণ তথ্য নেওয়া
    # -----------------------------------------------------

    placeholders = ",".join(
        "?"
        for _ in ids
    )

    try:

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

    except Exception:

        return []


    data_dict = {
        row[0]: row
        for row in data
    }

    results = [
        data_dict[item]
        for item in ids
        if item in data_dict
    ]

    return results


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
    # CREATE CONTEXT
    # =====================================================

    context_parts = []

    for row in search_results:

        book = row[1]
        page = row[2]
        text = row[3]

        # প্রতিটি পৃষ্ঠা থেকে সর্বোচ্চ ১০,০০০ অক্ষর
        text = text[:10000]

        context_parts.append(
            f"""
==================================================
কিতাবের নাম: {book}
PDF পৃষ্ঠা: {page}
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

আপনার কাছে লাইব্রেরি থেকে যে কিতাবের
অংশ সরবরাহ করা হয়েছে, তার ভিত্তিতেই
উত্তর প্রদান করবেন।

কঠোরভাবে নিচের নিয়মগুলো অনুসরণ করবেন:

১। নিজের মনগড়া তথ্য তৈরি করবেন না।

২। কনটেক্সটে তথ্য না থাকলে নিজের সাধারণ
জ্ঞান দিয়ে উত্তর বানাবেন না।

৩। কোনো আরবি ইবারত, হাদিস, ফতোয়া,
আলেমের বক্তব্য বা উদ্ধৃতি বানিয়ে লিখবেন না।

৪। কোনো পৃষ্ঠা নম্বর অনুমান করবেন না।

৫। শুধুমাত্র কনটেক্সটে দেওয়া কিতাবের নাম
ও PDF পৃষ্ঠা ব্যবহার করবেন।

৬। ব্যবহারকারী আরবি ইবারত চাইলে,
কনটেক্সটে থাকা আরবি ইবারতই প্রদান করবেন।

৭। ব্যবহারকারী বাংলা অনুবাদ চাইলে,
আরবি ইবারতের বাংলা অনুবাদ প্রদান করবেন।

৮। কোনো ইবারত অসম্পূর্ণ থাকলে নিজের পক্ষ
থেকে তা পূরণ করবেন না।

৯। একাধিক কিতাবে তথ্য থাকলে প্রয়োজন অনুযায়ী
একাধিক রেফারেন্স দিতে পারেন।

১০। উত্তর পরিষ্কার, সুন্দর ও গবেষণামূলক হবে।

১১। সম্ভব হলে প্রথমে আরবি ইবারত,
তারপর বাংলা অনুবাদ/ব্যাখ্যা দেবেন।

১২। কোনো কাল্পনিক রেফারেন্স তৈরি করবেন না।

১৩। কনটেক্সটে থাকা PDF পৃষ্ঠা পরিবর্তন করবেন না।

১৪। PDF পৃষ্ঠা এবং মূল কিতাবের পৃষ্ঠা
একই বিষয় নয়। তাই কেবল দেওয়া PDF
পৃষ্ঠা উল্লেখ করবেন।

১৫। তথ্য পাওয়া না গেলে অবশ্যই বলবেন:

"দুঃখিত, লাইব্রেরিতে সংরক্ষিত
কিতাবসমূহে এই বিষয়ে নির্ভরযোগ্য
তথ্য পাওয়া যায়নি।"

১৬। ব্যবহারকারী নির্দিষ্ট কোনো কিতাবের
নাম উল্লেখ করলে, কনটেক্সটে সেই কিতাবের
তথ্য থাকলে সেটিকে অগ্রাধিকার দেবেন।

১৭। আয়াত, হাদিস বা কোনো আলেমের বক্তব্য
উদ্ধৃত করার সময় কনটেক্সটে থাকা তথ্যের
বাইরে গিয়ে বানিয়ে লিখবেন না।

১৮। উত্তর শেষে রেফারেন্স দেবেন।

রেফারেন্স ফরম্যাট:

রেফারেন্স:
কিতাবের নাম — PDF পৃষ্ঠা

"""


    # =====================================================
    # GEMINI GENERATE
    # =====================================================

    client = get_gemini_client()

    response = client.models.generate_content(

        model="gemini-3.6-flash",

        contents=f"""

নিচে লাইব্রেরি থেকে পাওয়া
প্রাসঙ্গিক কিতাবের অংশ দেওয়া হলো:

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
# CHAT HISTORY
# =========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# =========================================================
# WELCOME SCREEN
# =========================================================

if len(st.session_state.messages) == 0:

    st.markdown(
        """
        <div class="welcome">

            <h2>কী জানতে চান?</h2>

            <p>
                আপনার প্রশ্ন লিখুন এবং
                আলা হযরত AI-কে জিজ্ঞাসা করুন।
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# SHOW CHAT
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# QUESTION INPUT
# =========================================================

prompt = st.chat_input(
    "আপনার প্রশ্ন লিখুন..."
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if prompt:

    # -----------------------------------------------------
    # User message
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):

        st.markdown(prompt)


    # -----------------------------------------------------
    # AI message
    # -----------------------------------------------------

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
                "দুঃখিত, এই মুহূর্তে উত্তর প্রদান "
                "করা সম্ভব হচ্ছে না। অনুগ্রহ করে "
                "কিছুক্ষণ পর আবার চেষ্টা করুন।"
            )

        st.markdown(answer)


    # -----------------------------------------------------
    # Save AI response
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
