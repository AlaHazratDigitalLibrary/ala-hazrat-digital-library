import sqlite3
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader


# ==============================
# FOLDER SETTINGS
# ==============================

BOOKS_FOLDER = Path("books")
DATA_FOLDER = Path("data")
DB_FILE = DATA_FOLDER / "library.db"


# ==============================
# TEXT NORMALIZATION
# ==============================

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

    return text.lower()


# ==============================
# BUILD DATABASE
# ==============================

def build_database():

    DATA_FOLDER.mkdir(
        exist_ok=True
    )

    # আগের database থাকলে মুছে ফেলবে
    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(
        DB_FILE
    )

    # মূল PDF page table
    conn.execute("""
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book TEXT NOT NULL,
            pdf_page INTEGER NOT NULL,
            text TEXT NOT NULL,
            search_text TEXT NOT NULL
        )
    """)

    # Search করার জন্য FTS
    conn.execute("""
        CREATE VIRTUAL TABLE pages_fts
        USING fts5(
            search_text,
            tokenize='unicode61 remove_diacritics 2'
        )
    """)

    # সব PDF খুঁজবে
    pdf_files = sorted(
        BOOKS_FOLDER.rglob("*.pdf")
    )

    print(
        f"মোট PDF পাওয়া গেছে: {len(pdf_files)}"
    )

    total_pages = 0

    # ==============================
    # PDF PROCESSING
    # ==============================

    for pdf_file in pdf_files:

        print(
            f"প্রসেস হচ্ছে: {pdf_file.name}"
        )

        try:

            reader = PdfReader(
                str(pdf_file)
            )

        except Exception as e:

            print(
                f"PDF খোলা যায়নি: {pdf_file.name}"
            )

            print(e)

            continue

        # প্রতিটি পৃষ্ঠা
        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            try:

                text = page.extract_text()

            except Exception:

                text = ""

            if not text:
                continue

            text = text.strip()

            if not text:
                continue

            # Search-এর জন্য normalized text
            search_text = normalize_text(
                text
            )

            # মূল page সংরক্ষণ
            cursor = conn.execute(
                """
                INSERT INTO pages
                (
                    book,
                    pdf_page,
                    text,
                    search_text
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    pdf_file.name,
                    page_number,
                    text,
                    search_text
                )
            )

            page_id = cursor.lastrowid

            # Search index
            conn.execute(
                """
                INSERT INTO pages_fts
                (
                    rowid,
                    search_text
                )
                VALUES (?, ?)
                """,
                (
                    page_id,
                    search_text
                )
            )

            total_pages += 1

        conn.commit()

    # Database optimize
    conn.execute(
        "VACUUM"
    )

    conn.close()

    print(
        "================================"
    )

    print(
        f"Index সম্পন্ন!"
    )

    print(
        f"মোট PDF: {len(pdf_files)}"
    )

    print(
        f"মোট Text page: {total_pages}"
    )

    print(
        "================================"
    )


# ==============================
# START
# ==============================

if __name__ == "__main__":

    build_database()
