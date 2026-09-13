import streamlit as st
from pypdf import PdfReader
from google import genai

# Streamlit Secrets থেকে API Key গ্রহণ
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# পেজ কনফিগারেশন
st.set_page_config(
    page_title="আলা হযরত ডিজিটাল লাইব্রেরি",
    page_icon="📚",
    layout="wide"
)

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
    .main-header h1 { margin: 0; color: #ffffff; font-size: 28px; }
    .main-header p { margin-top: 5px; color: #e0f2f1; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>📚 আলা হযরত ডিজিটাল লাইব্রেরি ও এআই অ্যাসিস্ট্যান্ট</h1>
        <p>ইমাম আহলে সুন্নাত শাহ আহমদ রযা খান রহ.-এর কিতাবভিত্তিক গবেষণা ও ফতোয়া অনুসন্ধান</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("📖 কিতাব ব্যবস্থাপনা")

uploaded_files = st.sidebar.file_uploader(
    "📥 কিতাব আপলোড করুন (PDF):", 
    type="pdf", 
    accept_multiple_files=True
)

@st.cache_data(show_spinner=False)
def extract_pdf_text(files):
    extracted_text = ""
    book_names = []
    for file in files:
        book_names.append(file.name)
        reader = PdfReader(file)
        max_pages = min(len(reader.pages), 150)
        for i in range(max_pages):
            page = reader.pages[i]
            t = page.extract_text()
            if t:
                extracted_text += f"\n--- [রেফারেন্স -> কিতাব: {file.name}, পৃষ্ঠা: {i+1}] ---\n" + t
    return extracted_text, book_names

pdf_texts = ""
book_names = []

if uploaded_files:
    with st.sidebar.status("কিতাব প্রসেস হচ্ছে...", expanded=True) as status:
        pdf_texts, book_names = extract_pdf_text(uploaded_files)
        status.update(label="কিতাব লোড সম্পন্ন!", state="complete", expanded=False)

if book_names:
    st.sidebar.markdown("### 📚 যুক্তকৃত কিতাবের তালিকা:")
    for b_name in book_names:
        st.sidebar.write(f"• {b_name}")

st.markdown("### 💬 কিতাব থেকে প্রশ্ন করুন")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("প্রশ্ন লিখুন..."):
    if not pdf_texts:
        st.warning("⚠️ দয়া করে সাইডবার থেকে অন্তত একটি PDF কিতাব আপলোড করুন।")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("উত্তর প্রস্তুত করা হচ্ছে..."):
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                context = pdf_texts[:150000]
                
                system_instruction = f"""
                আপনি আলা হযরত ইমাম আহমদ রযা খান রহ.-এর কিতাবসমূহের একজন প্রাজ্ঞ ও বিশ্বস্ত ফতোয়া অনুসন্ধানী এআই।
                
                ১. কেবল নিচে প্রদান করা কিতাবের কনটেক্সট অনুসরণ করে ব্যবহারকারীর প্রশ্নের উত্তর দিন।
                ২. উত্তরের শেষে অবশ্যই কিতাবের নাম ও পৃষ্ঠা নম্বর (রেফারেন্স) উল্লেখ করুন।
                ৩. যদি প্রশ্নের উত্তর প্রদত্ত কিতাবে না থাকে, তবে বলুন: "দুঃখিত, আপনার আপলোডকৃত কিতাবে এই বিষয়ে কোনো তথ্য পাওয়া যায়নি।"
                
                কনটেক্সট:
                {context}
                """
                
                # আপডেট করা Gemini মডেল ব্যবহার করা হয়েছে
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"{system_instruction}\n\nপ্রশ্ন: {prompt}"
                )
                answer = response.text
            except Exception as e:
                answer = f"ত্রুটি ঘটেছে: {e}"
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
