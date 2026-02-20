import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from io import BytesIO
import json
import re
import PyPDF2

# --- 1. SETTINGS ---
st.set_page_config(page_title="Generator Soal Muhammadiyah", layout="wide")

def clean_option(opt):
    """Fungsi yang lebih kuat untuk menghapus label ganda (A. A. -> Kosong)"""
    if not opt: return ""
    text = str(opt)
    # Menghapus pola seperti "A. ", "A. A. ", "1. A. " di awal teks
    for _ in range(3):
        text = re.sub(r'^[A-Ea-e0-9]\.?\s*', '', text).strip()
    return text

# --- 2. DOKUMEN GENERATOR (KISI-KISI & KARTU SOAL TETAP ADA) ---
def create_header(doc, info):
    p = doc.add_paragraph(); p.alignment = 1 # Center
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); r.bold = True
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); r.bold = True
    r = p.add_run(f"{info.get('sekolah')}\n"); r.font.size = Pt(14); r.bold = True
    doc.add_paragraph("_" * 75)

# --- 3. LOGIKA UTAMA ---
if 'files' not in st.session_state: st.session_state.files = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    # ... (input identitas lainnya)

st.title("🚀 Generator Administrasi Soal Lengkap")

uploaded_file = st.file_uploader("Unggah Materi (PDF/DOCX)", type=['pdf', 'docx'])

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Ekstraksi materi
        materi_text = ""
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                reader = PyPDF2.PdfReader(uploaded_file)
                materi_text = "".join([p.extract_text() for p in reader.pages])
        
        # Perintah ke AI agar tidak membuat label abjad sendiri
        prompt = f"Buat soal dari materi ini: {materi_text[:5000]}. Format JSON murni. JANGAN sertakan label A, B, C pada isi opsi."
        
        with st.spinner("Sedang meramu soal..."):
            res = model.generate_content(prompt)
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                # Simpan hasil ke session state agar tombol cetak muncul
                st.session_state.preview_data = data
                # Panggil fungsi generator dokumen Anda di sini...
                st.success("Selesai! Tombol unduh sudah muncul di bawah.")
                
    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")

# --- 4. TOMBOL CETAK ---
if st.session_state.get('preview_data'):
    st.divider()
    st.subheader("📥 Unduh Administrasi Lengkap")
    # Tampilkan tombol download Naskah, Kisi-kisi, dan Kartu Soal di sini
