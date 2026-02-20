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

# --- 1. SETTINGS & UTILS ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah 1 Weleri", layout="wide")

def clean_json_output(text):
    """Membersihkan output AI agar hanya mengambil blok JSON murni."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group() if match else text

def clean_option(opt):
    """Menghapus label abjad ganda agar tidak muncul A. A. atau B. B."""
    if not opt: return ""
    text = str(opt)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS (Sesuai Template User) ---

def create_header(doc, info):
    """Header sesuai BENTUK FORMAT SOAL ATS GENAP.docx [cite: 1]"""
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info['jenis_asesmen'].upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(2, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']}")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

def generate_naskah(data_soal, info):
    doc = Document(); create_header(doc, info)
    no = 1
    # Loop melalui setiap kategori soal (PG, Uraian, Isian, dll)
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        doc.add_paragraph().add_run(f"\n{tipe.upper()}").bold = True
        for q in quests:
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            elif "Benar / Salah" in tipe:
                doc.add_paragraph("    ( ) Benar   ( ) Salah")
            no += 1
    return doc

def generate_kisi_kisi(data_soal, info):
    """Sesuai format KISI-KISI.docx """
    doc = Document()
    doc.add_heading(f"KISI-KISI SOAL {info['jenis_asesmen']}", 1)
    table = doc.add_table(1, 6); table.style = 'Table Grid'
    headers = ["No", "TP/KD", "Indikator Soal", "Level", "Bentuk Soal", "No Soal"]
    for i, h in enumerate(headers): table.rows[0].cells[i].text = h
    
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            row = table.add_row().cells
            row[0].text = str(idx)
            row[2].text = q.get('indikator', '-')
            row[3].text = q.get('level', 'L2')
            row[4].text = tipe
            row[5].text = str(idx)
            idx += 1
    return doc

def generate_kartu(data_soal, info):
    """Sesuai format KARTU SOAL.docx """
    doc = Document()
    doc.add_heading("KARTU SOAL", 1)
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            tbl = doc.add_table(5, 2); tbl.style = 'Table Grid'
            tbl.cell(0, 0).text = "Nomor Soal"; tbl.cell(0, 1).text = str(idx)
            tbl.cell(1, 0).text = "Indikator"; tbl.cell(1, 1).text = q.get('indikator', '-')
            tbl.cell(2, 0).text = "Butir Soal"; tbl.cell(2, 1).text = q.get('soal', '')
            tbl.cell(3, 0).text = "Kunci/Pedoman"; tbl.cell(3, 1).text = str(q.get('kunci', q.get('pedoman', '-')))
            tbl.cell(4, 0).text = "Skor"; tbl.cell(4, 1).text = str(q.get('skor', 5))
            doc.add_paragraph()
            idx += 1
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal v5.0")

jenis_asesmen = st.selectbox("Peruntukan Soal", [
    "Asesmen Formatif", "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"
])

uploaded_file = st.file_uploader("Unggah Materi (PDF)", type=['pdf'])
# Menambahkan pilihan bentuk soal sesuai permintaan
bentuk_soal = st.multiselect("Bentuk Soal", 
    ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], 
    default=["Pilihan Ganda", "Uraian"])

conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        # Deteksi model otomatis untuk menghindari error 404
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
        
        materi_text = ""
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_text = " ".join([p.extract_text() for p in reader.pages])

        model = genai.GenerativeModel(target_model)
        # Prompt yang lebih ketat agar JSON valid dan tidak ada teks tambahan
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi_text[:6000]}. 
        Jumlah: {json.dumps(conf)}. 
        WAJIB OUTPUT JSON MURNI: {{ "Kategori": [ {{ "soal": "", "opsi": [], "kunci": "", "indikator": "", "skor": 0, "pedoman": "", "level": "L2" }} ] }}
        Jangan beri penjelasan di luar JSON. Untuk PG Kompleks, sertakan lebih dari satu jawaban benar di field kunci."""

        with st.spinner(f"Memproses dengan {target_model}..."):
            res = model.generate_content(prompt)
            data = json.loads(clean_json_output(res.text))
            
            st.session_state.preview_data = data
            info_dict = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            
            # Generate dokumen secara otomatis
            st.session_state.files = {
                'n': generate_naskah(data, info_dict),
                'k': generate_kisi_kisi(data, info_dict),
                's': generate_kartu(data, info_dict)
            }
            st.success("Administrasi berhasil dibuat!")
            
    except Exception as e:
        st.error(f"Gagal memproses: {e}. Silakan coba klik tombol 'Proses Data' sekali lagi.")

# --- 4. OUTPUT ---
if 'files' in st.session_state:
    st.divider()
    c1, c2, c3 = st.columns(3)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    c1.download_button("📝 Unduh Naskah", to_io(st.session_state.files['n']), "Naskah_Soal.docx", "primary")
    c2.download_button("🔑 Unduh Kisi-kisi", to_io(st.session_state.files['k']), "Kisi_Kisi.docx")
    c3.download_button("🗂️ Unduh Kartu Soal", to_io(st.session_state.files['s']), "Kartu_Soal.docx")

    # Preview Visual
    st.subheader("👁️ Preview Soal")
    for tipe, quests in st.session_state.preview_data.items():
        with st.expander(f"Tipe: {tipe}"):
            for i, q in enumerate(quests):
                st.write(f"**{i+1}. {q.get('soal')}**")
                st.caption(f"Kunci: {q.get('kunci')} | Skor: {q.get('skor')}")
