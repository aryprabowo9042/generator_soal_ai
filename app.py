import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re
import pandas as pd

# --- 1. SETTINGS & UTILITIES ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def t(value):
    return str(value) if value is not None else ""

# Fungsi untuk membersihkan label ganda (A. A. -> Teks)
def clean_option(opt):
    # Menghapus pola seperti "A. ", "A. A. ", "1. ", dsb di awal string
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', str(opt))
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', cleaned) # Double check jika ada label ganda
    return cleaned.strip()

def set_font(run, size=11, bold=False, font_name='Times New Roman'):
    try:
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
        run.font.size = Pt(int(size))
        run.bold = bold
    except:
        pass

# --- 2. DOKUMEN GENERATORS ---

def generate_docs_final(data_soal, info):
    # --- DOKUMEN 1: NASKAH SOAL ---
    d1 = Document()
    p = d1.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{t(info['sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info['tahun'])}\n"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    tbl = d1.add_table(3, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"KELAS : {info['kelas']}"),
        (f"HARI/TANGGAL : .................", f"SEMESTER : {info['semester']}"),
        (f"GURU PENGAMPU : {info['guru']}", f"WAKTU : 90 Menit")
    ]
    for i, (left, right) in enumerate(rows):
        r1 = tbl.rows[i].cells[0].paragraphs[0].add_run(left); set_font(r1, 10)
        r2 = tbl.rows[i].cells[1].paragraphs[0].add_run(right); set_font(r2, 10)

    d1.add_paragraph()
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        d1.add_paragraph().add_run(f"\n{tipe.upper()}").bold = True
        for q in quests:
            # Menghapus label nomor jika AI sudah menyertakannya
            soal_text = re.sub(r'^\d+\.\s*', '', q.get('soal', ''))
            d1.add_paragraph(f"{no}. {soal_text}")
            
            if "Pilihan Ganda" in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    label = ['A','B','C','D'][i]
                    d1.add_paragraph(f"    {label}. {clean_option(o)}")
            no += 1

    # --- DOKUMEN 2: KUNCI & PEDOMAN ---
    d2 = Document()
    d2.add_heading(f"KUNCI JAWABAN & PEDOMAN PENSKORAN", 0)
    ktbl = d2.add_table(1, 4); ktbl.style = 'Table Grid'
    for i, h in enumerate(["No", "Bentuk", "Kunci/Pedoman", "Skor"]): ktbl.rows[0].cells[i].text = h
    
    idx = 1
    for tipe, qs in data_soal.items():
        for q in qs:
            row = ktbl.add_row().cells
            row[0].text = str(idx); row[1].text = tipe
            row[2].text = str(q.get('kunci', q.get('pedoman', '-')))
            row[3].text = str(q.get('skor', 0))
            idx += 1
            
    return d1, d2

# --- 3. UI STREAMLIT ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Nama Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("✅ Generator Soal SMP Muhammadiyah")

jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester",
    "Asesmen Formatif Lingkup Materi"
])

bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 40, 5) for b in bentuk_soal}
materi = st.text_area("Materi / Kisi-kisi", height=150)

if st.button("🚀 PROSES DATA"):
    if api_key and materi:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0])
            
            prompt = f"Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi}. Jumlah: {json.dumps(conf)}. TOTAL SKOR 100. Berikan JSON murni tanpa label A/B/C di dalam value opsi."
            
            res = model.generate_content(prompt)
            data = json.loads(re.sub(r'```json|```', '', res.text).strip())
            
            info = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            d1, d2 = generate_docs_final(data, info)
            
            st.session_state.preview_data = data
            st.session_state.files = {'n': d1, 'k': d2}
            st.success("Berhasil dibuat!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. PREVIEW & DOWNLOAD ---
if 'files' in st.session_state:
    c1, c2 = st.columns(2)
    def to_io(d):
        io = BytesIO(); d.save(io); return io.getvalue()
    
    c1.download_button("📥 Naskah Soal", to_io(st.session_state.files['n']), "Naskah.docx")
    c2.download_button("📥 Kunci Jawaban", to_io(st.session_state.files['k']), "Kunci.docx")
    
    st.subheader("👁️ Preview Soal")
    for tipe, qs in st.session_state.preview_data.items():
        st.write(f"**{tipe}**")
        for i, q in enumerate(qs):
            st.write(f"{i+1}. {q['soal']}")
            if "Pilihan Ganda" in tipe:
                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;{ [f'{chr(65+j)}. {clean_option(opt)}' for j, opt in enumerate(q['opsi'])] }")
