import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re
import PyPDF2

# --- UTILS ---
def clean_option(opt):
    """Mencegah label ganda (A. A. -> Jawaban)"""
    if not opt: return ""
    t = str(opt)
    # Hapus pola abjad di awal hingga 2 lapis
    t = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', t).strip()
    t = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', t).strip()
    return t

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- GENERATORS ---
def create_header(doc, info):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info.get('sekolah')}\n"); set_font(r, 14, True)
    doc.add_paragraph("_" * 75)

def generate_naskah(data_soal, info):
    doc = Document(); create_header(doc, info)
    no = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        doc.add_paragraph().add_run(f"\n{str(tipe).upper()}").bold = True
        for q in quests:
            if not isinstance(q, dict): continue
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in str(tipe):
                opsi = q.get('opsi', [])
                for i, o in enumerate(opsi[:4]):
                    doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            no += 1
    return doc

# --- UI ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah")
if 'preview_data' not in st.session_state: st.session_state.preview_data = None
if 'files' not in st.session_state: st.session_state.files = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "Ary Prabowo")
    mapel = st.text_input("Mapel", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun", "2025/2026")

st.title("📝 Generator Administrasi Soal")

uploaded_file = st.file_uploader("Unggah Materi (PDF)", type=['pdf'])
materi_teks = st.text_area("Atau masukkan teks materi di sini")

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    # Ekstrak PDF jika ada
    final_materi = materi_teks
    if uploaded_file:
        reader = PyPDF2.PdfReader(uploaded_file)
        final_materi = " ".join([p.extract_text() for p in reader.pages])

    try:
        genai.configure(api_key=api_key)
        # Cari model yang aktif secara otomatis
        m_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        active_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in m_list else m_list[0]
        
        model = genai.GenerativeModel(active_model)
        prompt = f"Buat soal {mapel} dari materi: {final_materi[:5000]}. Format JSON: {{'Pilihan Ganda': [{{'soal':'','opsi':['','','',''],'kunci':'','indikator':''}}]}}. JANGAN beri abjad A/B/C di dalam list opsi."
        
        with st.spinner(f"Memproses dengan {active_model}..."):
            res = model.generate_content(prompt)
            data = json.loads(re.search(r'\{.*\}', res.text, re.DOTALL).group())
            st.session_state.preview_data = data
            info_dict = {'sekolah':sekolah, 'guru':guru, 'mapel':mapel, 'kelas':kelas, 'semester':semester, 'tahun':tahun}
            st.session_state.files = {'n': generate_naskah(data, info_dict)}
            st.success("Berhasil! Tombol unduh muncul di bawah.")
    except Exception as e:
        st.error(f"Kesalahan: {e}")

# --- DOWNLOAD ---
if st.session_state.files:
    bio = BytesIO(); st.session_state.files['n'].save(bio)
    st.download_button("📥 Unduh Naskah Soal", bio.getvalue(), "Naskah.docx", "primary")
