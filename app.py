import streamlit as st
from pypdf import PdfReader
from google import genai

# ১. পেজ কনফিগারেশন ও থিম
st.set_page_config(
    page_title="আলা হযরত ডিজিটাল লাইব্রেরি",
    page_icon="📚",
    layout="wide"
)

# সিএসএস দিয়ে সুন্দর কালার ও ইন্টারফেস ডিজাইন (ইসলামিক গ্রিন থিম)
st.markdown("""
    <style>
    .main-header {
        background-color: #075e54;
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .main-header h1 {
        margin: 0;
        font-size: 32px;
        color: #ffffff;
    }
    .main-header p {
        font-size: 16px;
        margin-top: 8px;
        color: #e0f2f1;
    }
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ২. মূল হেডার ও পরিচিতি
st.markdown("""
    <div class="main-header">
        <h1>📚 আলা হযরত ডিজিটাল লাইব্রেরি ও এআই অ্যাসিস্ট্যান্ট</h1>
        <p>ইমাম আহলে সুন্নাত, আলা হযরত শাহ আহমদ রযা খান বেরলভী রহ.-এর কিতাবভিত্তিক গবেষণা ও ফতোয়া অনুসন্ধান</p>
    </div>
""", unsafe_allow_html=True)

# ৩. সাইডবার (কিতাব ব্যবস্থাপনা ও সেটিং)
st.sidebar.title("📖 কিতাব ব্যবস্থাপনা")
st.sidebar.info("আলা হযরতের যেকোনো ফতোয়া বা কিতাবের PDF এখানে আপলোড করুন।")

# API Key নেওয়ার ব্যবস্থা
api_key = st.sidebar.text_input("🔑 Gemini API Key দিন:", type="password", help="aistudio.google.com থেকে ফ্রি API Key নিয়ে এখানে দিন")

# PDF কিতাব আপলোড
uploaded_files = st.sidebar.file_uploader(
    "📥 কিতাব আপলোড করুন (PDF):", 
    type="pdf", 
    accept_multiple_files=True
)

if "pdf_texts" not in st.session_state:
    st.session_state.pdf_texts = ""

if "book_names" not in st.session_state:
    st.session_state.book_names = []

# ফাইল প্রসেসিং লজিক (রেফারেন্স বা পৃষ্ঠা নম্বরসহ টেক্সট সাজানো)
if uploaded_files:
    full_text = ""
    st.session_state.book_names = [file.name for file in uploaded_files]
    
    with st.sidebar.status("কিতাব প্রসেস করা হচ্ছে...", expanded=True) as status:
        for file in uploaded_files:
            reader = PdfReader(file)
            for i, page in enumerate(reader.pages):
                t = page.extract_text()
                if t:
                    full_text += f"\n--- [রেফারেন্স -> কিতাব: {file.name}, পৃষ্ঠা: {i+1}] ---\n" + t
        status.update(label="সকল কিতাব সফলভাবে লোড হয়েছে!", state="complete", expanded=False)
    
    st.session_state.pdf_texts = full_text

# সাইডবারে আপলোডকৃত কিতাবের নাম প্রদর্শন
if st.session_state.book_names:
    st.sidebar.markdown("### 📚 যুক্তকৃত কিতাবের তালিকা:")
    for b_name in st.session_state.book_names:
        st.sidebar.write(f"• {b_name}")

# ৪. চ্যাট ইন্টারফেস ও ব্যাকএন্ড লজিক
st.markdown("### 💬 কিতাব থেকে প্রশ্ন করুন")

if "messages" not in st.session_state:
    st.session_state.messages = []

# আগের চ্যাট হিস্ট্রি দেখানো
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ইউজারের প্রশ্ন গ্রহণ
if prompt := st.chat_input("যেমন: ইমান ও আকিদা বিষয়ে আলা হযরত কিতাবে কী লিখেছেন?"):
    if not api_key:
        st.error("⚠️ দয়া করে সাইডবারে আপনার Gemini API Key প্রদান করুন।")
        st.stop()
        
    if not st.session_state.pdf_texts:
        st.warning("⚠️ দয়া করে সাইডবার থেকে অন্তত একটি কিতাবের (PDF) ফাইল আপলোড করুন।")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("কিতাবের পৃষ্ঠা অনুসন্ধান ও উত্তর প্রস্তুত করা হচ্ছে..."):
            try:
                client = genai.Client(api_key=api_key)
                
                # কনটেক্সট লিমিট হ্যান্ডেল করা
                context = st.session_state.pdf_texts[:150000]
                
                system_instruction = f"""
                আপনি আলা হযরত ইমাম আহমদ রযা খান রহ.-এর কিতাবসমূহের একজন প্রাজ্ঞ ও বিশ্বস্ত ফতোয়া অনুসন্ধানী এআই।
                
                আপনার মূল কাজসমূহ:
                ১. কেবল নিচে প্রদান করা কিতাবের কনটেক্সট অনুসরণ করে ব্যবহারকারীর প্রশ্নের উত্তর দিন।
                ২. উত্তরের শেষে অবশ্যই কিতাবের নাম ও পৃষ্ঠা নম্বর (রেফারেন্স) সুস্পষ্টভাবে উল্লেখ করুন।
                ৩. যদি প্রশ্নের উত্তর প্রদত্ত কিতাবগুলোর মধ্যে না থাকে, তবে বানোয়াট কোনো তথ্য দেবেন না। বিনয়ের সাথে সরাসরি বলুন: "দুঃখিত, আপনার আপলোডকৃত কিতাবে এই বিষয়ে কোনো তথ্য বা মাসয়ালা পাওয়া যায়নি।"
                
                কনটেক্সট (উপলব্ধ কিতাবের অংশ):
                {context}
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"{system_instruction}\n\nপ্রশ্ন: {prompt}"
                )
                answer = response.text
            except Exception as e:
                answer = f"ত্রুটি ঘটেছে: {e}"
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
