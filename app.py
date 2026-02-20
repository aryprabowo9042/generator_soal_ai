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

# --- 1. KONFIGURASI ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah 1 Weleri", layout="wide")

def clean_json_output(text):
    """Menghapus teks tambahan di luar kurung kurawal JSON"""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group() if match else text

def clean_option(opt):
    if not opt: return ""
    text = str(opt)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

# --- 2. GENERATOR DOKUMEN (SESUAI TEMPLATE USER) ---

def create_header(doc, info):
    """Header sesuai BENTUK FORMAT SOAL ATS GENAP.docx [cite: 1, 2, 3, 4, 5]"""
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); r.bold = True
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); r.bold = True
    r = p.add_run(f"{info['sekolah']}\n"); r.font.size = Pt(14); r.bold = True
    r = p.add_run(f"{info['jenis_asesmen'].upper()}\n"); r.bold = True
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); r.bold = True
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(2, 2)
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']}")
    ]
    for i, (left, right) in enumerate(rows):
        tbl.rows[i].cells[0].text = left
        tbl.rows[i].cells[1].text = right

def generate_docx(data_soal, info):
    doc = Document()
    create_header(doc, info)
    no = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        doc.add_paragraph().add_run(f"\n{tipe.upper()}").bold = True
        
        for q in quests:
            if not isinstance(q, dict): continue
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            
            if "Pilihan Ganda" in tipe and "Kompleks" not in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            elif "Pilihan Ganda Kompleks" in tipe:
                for i, o in enumerate(q.get('opsi', [])):
                    doc.add_paragraph(f"    [ ] {clean_option(o)}")
            elif "Benar / Salah" in tipe:
                doc.add_paragraph("    ( ) Benar  ( ) Salah")
            no += 1
    return doc

# --- 3. UI STREAMLIT ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI") [cite: 3]
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya") [cite: 33]
    kelas = st.text_input("Kelas", "IX") [cite: 34]
    tahun = st.text_input("Tahun Pelajaran", "2025/2026") [cite: 31]

st.title("🚀 Smart Generator Administrasi Soal")

jenis_asesmen = st.selectbox("Peruntukan Soal", [
    "Asesmen Formatif", "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"
])

uploaded_file = st.file_uploader("Unggah Materi (PDF)", type=['pdf'])
bentuk_soal = st.multiselect("Bentuk Soal", 
    ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], 
    default=["Pilihan Ganda", "Isian Singkat", "Uraian"])

conf = {b: st.number_input(f"Jumlah {b}", 1, 20, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        # Auto-Discovery Model
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        active_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
        
        materi = ""
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi = " ".join([p.extract_text() for p in reader.pages])

        model = genai.GenerativeModel(active_model)
        
        # PROMPT KETAT UNTUK MENGHINDARI EXTRA DATA ERROR
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi[:6000]}.
        Jumlah: {json.dumps(conf)}.
        OUTPUT HARUS HANYA JSON MURNI TANPA TEKS LAIN.
        Struktur: {{ "Tipe": [ {{ "soal": "", "opsi": [], "kunci": "", "indikator": "", "skor": 0 }} ] }}
        Untuk Pilihan Ganda Kompleks, berikan minimal 2 jawaban benar di 'kunci'."""

        with st.spinner(f"Memproses dengan {active_model}..."):
            res = model.generate_content(prompt)
            clean_res = clean_json_output(res.text)
            data = json.loads(clean_res)
            
            st.session_state.preview_data = data
            info = {'sekolah': sekolah, 'mapel': mapel, 'kelas': kelas, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen, 'semester': 'Genap'}
            st.session_state.docx = generate_docx(data, info)
            st.success("Administrasi Berhasil Dibuat!")
            
    except Exception as e:
        st.error(f"Gagal memproses: {e}. Coba klik 'Proses Data' lagi.")

# --- 4. PREVIEW & DOWNLOAD ---
if 'preview_data' in st.session_state:
    bio = BytesIO()
    st.session_state.docx.save(bio)
    st.download_button("📥 Unduh Naskah Soal (.docx)", bio.getvalue(), "Naskah_Soal.docx", "primary")
    
    for tipe, qs in st.session_state.preview_data.items():
        with st.expander(f"Preview {tipe}"):
            for i, q in enumerate(qs):
                st.write(f"**{i+1}. {q.get('soal')}**")
                if "opsi" in q and q["opsi"]:
                    st.write(f"Opsi: {q['opsi']}")
                st.caption(f"Kunci: {q.get('kunci')} | Skor: {q.get('skor')}")
