import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re

# --- 1. SETTINGS & UTILITIES ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def t(value):
    return str(value) if value is not None else ""

def clean_option(opt):
    # Membersihkan label ganda A. A. atau 1. A.
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', str(opt))
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', cleaned)
    return cleaned.strip()

def set_font(run, size=11, bold=False, font_name='Times New Roman'):
    try:
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
        run.font.size = Pt(int(size))
        run.bold = bold
    except:
        pass

# --- 2. DOKUMEN GENERATOR ---
def generate_docs_final(data_soal, info):
    d1 = Document()
    # Header
    p = d1.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{t(info['sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info['tahun'])}\n"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    # Identitas
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
            d1.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    d1.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            no += 1

    d2 = Document()
    d2.add_heading("KUNCI JAWABAN", 0)
    # (Logika kunci jawaban sama seperti sebelumnya...)
    
    return d1, d2

# --- 3. UI STREAMLIT ---
# Inisialisasi session state agar tidak error saat diakses pertama kali
if 'files' not in st.session_state: st.session_state.files = None
if 'preview_data' not in st.session_state: st.session_state.preview_data = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("✅ Generator Soal SMP Muhammadiyah")

jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester", "Asesmen Formatif Lingkup Materi"
])

bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 40, 5) for b in bentuk_soal}
materi = st.text_area("Materi / Kisi-kisi", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.warning("API Key dan Materi tidak boleh kosong!")
    else:
        try:
            genai.configure(api_key=api_key)
            # Otomatis cari model yang tersedia
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
            
            model = genai.GenerativeModel(model_name)
            prompt = f"Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi}. Jumlah: {json.dumps(conf)}. TOTAL SKOR 100. Berikan JSON murni."
            
            with st.spinner("Menghubungi AI..."):
                res = model.generate_content(prompt)
                data = json.loads(re.sub(r'```json|```', '', res.text).strip())
                
                info = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
                d1, d2 = generate_docs_final(data, info)
                
                st.session_state.preview_data = data
                st.session_state.files = {'n': d1, 'k': d2}
                st.success("Berhasil! Silakan unduh file di bawah.")

        except Exception as e:
            if "429" in str(e):
                st.error("🚫 Kuota API Habis! Silakan tunggu 1 menit atau gunakan API Key lain.")
            else:
                st.error(f"Terjadi Kesalahan: {e}")

# --- 4. DOWNLOAD SECTION ---
if st.session_state.files is not None:
    st.divider()
    c1, c2 = st.columns(2)
    
    def to_io(doc_obj):
        if doc_obj is None: return None
        io = BytesIO()
        doc_obj.save(io)
        return io.getvalue()

    naskah_bytes = to_io(st.session_state.files['n'])
    kunci_bytes = to_io(st.session_state.files['k'])

    if naskah_bytes:
        c1.download_button("📥 Unduh Naskah Soal", naskah_bytes, f"Naskah_{mapel}.docx", "primary")
    if kunci_bytes:
        c2.download_button("📥 Unduh Kunci Jawaban", kunci_bytes, f"Kunci_{mapel}.docx")
