import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re

# --- 1. SETTINGS & UTILITIES ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def clean_option(opt):
    """Menghapus label ganda seperti 'A. A. Jawaban'"""
    if not opt or not isinstance(opt, str): return str(opt)
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', opt)
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', cleaned)
    return cleaned.strip()

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS (DENGAN PROTEKSI TIPE DATA) ---

def create_header(doc, info):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info.get('sekolah', '')}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info.get('jenis_asesmen', '').upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info.get('tahun', '')}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(3, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info.get('mapel', '')}", f"KELAS : {info.get('kelas', '')}"),
        (f"HARI/TANGGAL : .................", f"SEMESTER : {info.get('semester', '')}"),
        (f"GURU PENGAMPU : {info.get('guru', '')}", f"WAKTU : 90 Menit")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

def generate_naskah(data_soal, info):
    doc = Document(); create_header(doc, info)
    no = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        doc.add_paragraph().add_run(f"{str(tipe).upper()}").bold = True
        for q in quests:
            if not isinstance(q, dict): continue # PROTEKSI UTAMA
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in str(tipe):
                opsi = q.get('opsi', [])
                if isinstance(opsi, list):
                    for i, o in enumerate(opsi[:4]):
                        doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            no += 1
    return doc

def generate_kisi_kunci(data_soal, info):
    doc = Document()
    doc.add_heading(f"KISI-KISI & KUNCI JAWABAN", 0)
    table = doc.add_table(1, 6); table.style = 'Table Grid'
    hdrs = ["No", "Indikator", "Bentuk", "Kunci/Pedoman", "Skor", "Level"]
    for i, h in enumerate(hdrs): table.rows[0].cells[i].text = h
    
    idx = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        for q in quests:
            if not isinstance(q, dict): continue # PROTEKSI UTAMA
            row = table.add_row().cells
            row[0].text = str(idx)
            row[1].text = str(q.get('indikator', '-'))
            row[2].text = str(tipe)
            row[3].text = str(q.get('kunci', q.get('pedoman', '-')))
            row[4].text = str(q.get('skor', 0))
            row[5].text = str(q.get('level', 'L2'))
            idx += 1
    return doc

def generate_kartu(data_soal, info):
    doc = Document()
    doc.add_heading("KARTU SOAL", 0)
    idx = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        for q in quests:
            if not isinstance(q, dict): continue # PROTEKSI UTAMA
            tbl = doc.add_table(4, 2); tbl.style = 'Table Grid'
            tbl.cell(0, 0).text = f"No Soal: {idx}"; tbl.cell(0, 1).text = f"Bentuk: {str(tipe)}"
            tbl.cell(1, 0).merge(tbl.cell(1, 1)).text = f"Indikator: {str(q.get('indikator', '-'))}"
            tbl.cell(2, 0).merge(tbl.cell(2, 1)).text = f"Soal: {str(q.get('soal', ''))}"
            tbl.cell(3, 0).text = f"Kunci: {str(q.get('kunci', '-'))}"; tbl.cell(3, 1).text = f"Skor: {str(q.get('skor', 0))}"
            doc.add_paragraph()
            idx += 1
    return doc

# --- 3. UI STREAMLIT ---
if 'preview_data' not in st.session_state: st.session_state.preview_data = None
if 'files' not in st.session_state: st.session_state.files = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal")

jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester", "Asesmen Formatif Lingkup Materi"
])

bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 50, 5) for b in bentuk_soal}
materi = st.text_area("Masukkan Materi / Kisi-kisi", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Masukkan API Key!"); st.stop()
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        active_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
        
        model = genai.GenerativeModel(active_model)
        # PROMPT LEBIH KETAT
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi}. 
        Jumlah: {json.dumps(conf)}. TOTAL SKOR 100.
        WAJIB memberikan output dalam format JSON murni dengan struktur:
        {{ "Tipe Soal": [ {{ "soal": "isi", "opsi": ["A", "B", "C", "D"], "kunci": "A", "indikator": "...", "skor": 2, "level": "L1" }} ] }}
        Jangan memberikan teks penjelasan apa pun."""
        
        with st.spinner("AI sedang memproses..."):
            res = model.generate_content(prompt)
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if match:
                raw_data = json.loads(match.group())
                
                # Validasi agar data_soal harus berupa dictionary
                if isinstance(raw_data, dict):
                    st.session_state.preview_data = raw_data
                    info_dict = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
                    
                    # Generate Dokumen
                    st.session_state.files = {
                        'n': generate_naskah(raw_data, info_dict),
                        'k': generate_kisi_kunci(raw_data, info_dict),
                        's': generate_kartu(raw_data, info_dict)
                    }
                    st.success("Data berhasil diolah!")
                else:
                    st.error("Format JSON AI tidak sesuai (Bukan Dictionary).")
            else:
                st.error("AI tidak memberikan JSON yang valid.")
    except Exception as e:
        st.error(f"Kesalahan Sistem: {e}")

# --- 4. TAMPILAN DOWNLOAD & PREVIEW ---
if st.session_state.files and st.session_state.preview_data:
    st.divider()
    c1, c2, c3 = st.columns(3)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    c1.download_button("📝 Cetak Naskah", to_io(st.session_state.files['n']), "Naskah_Soal.docx", "primary")
    c2.download_button("🔑 Cetak Kisi & Kunci", to_io(st.session_state.files['k']), "Kisi_dan_Kunci.docx")
    c3.download_button("🗂️ Cetak Kartu Soal", to_io(st.session_state.files['s']), "Kartu_Soal.docx")

    st.divider()
    st.subheader("👁️ Preview Soal")
    for tipe, qs in st.session_state.preview_data.items():
        if not isinstance(qs, list): continue
        with st.expander(f"Bagian: {tipe}"):
            for i, q in enumerate(qs):
                if isinstance(q, dict):
                    st.write(f"**{i+1}. {q.get('soal', '')}**")
                    st.caption(f"Kunci: {q.get('kunci', q.get('pedoman', '-'))} | Skor: {q.get('skor', 0)}")
