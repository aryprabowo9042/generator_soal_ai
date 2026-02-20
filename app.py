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
    """Mengambil string di antara kurung kurawal pertama dan terakhir."""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            return text[start:end]
        return text
    except:
        return text

def clean_option(opt):
    if not opt: return ""
    text = str(opt)
    # Menghapus label abjad ganda (A. A. -> isi)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS ---

def create_header(doc, info):
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

def generate_naskah(data_list, info):
    doc = Document(); create_header(doc, info)
    # Kelompokkan soal berdasarkan tipe
    grouped = {}
    for q in data_list:
        t = q.get('tipe', 'Lainnya')
        if t not in grouped: grouped[t] = []
        grouped[t].append(q)
    
    no = 1
    for tipe, quests in grouped.items():
        doc.add_paragraph().add_run(f"\n{tipe.upper()}").bold = True
        for q in quests:
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in tipe:
                opsi = q.get('opsi', [])
                labels = ['A','B','C','D']
                for i, o in enumerate(opsi[:4]):
                    doc.add_paragraph(f"    {labels[i]}. {clean_option(o)}")
            elif "Benar / Salah" in tipe:
                doc.add_paragraph("    ( ) Benar   ( ) Salah")
            no += 1
    return doc

# (Fungsi Kisi-kisi dan Kartu Soal disesuaikan dengan data_list)
def generate_kisi_kisi(data_list, info):
    doc = Document()
    doc.add_heading(f"KISI-KISI SOAL {info['jenis_asesmen']}", 1)
    table = doc.add_table(1, 6); table.style = 'Table Grid'
    for i, h in enumerate(["No", "TP/KD", "Indikator Soal", "Level", "Bentuk Soal", "No Soal"]):
        table.rows[0].cells[i].text = h
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1); row[2].text = q.get('indikator', '-'); row[3].text = q.get('level', 'L2')
        row[4].text = q.get('tipe', '-'); row[5].text = str(i+1)
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal v5.1")

jenis_asesmen = st.selectbox("Peruntukan Soal", [
    "Asesmen Formatif", "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"
])

uploaded_file = st.file_uploader("Unggah Materi (PDF)", type=['pdf'])
bentuk_soal = st.multiselect("Bentuk Soal", 
    ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], 
    default=["Pilihan Ganda", "Uraian"])

conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        materi_text = ""
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_text = " ".join([p.extract_text() for p in reader.pages])

        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # PROMPT LEBIH STABIL DENGAN FLAT LIST
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen} berdasarkan materi: {materi_text[:6000]}.
        Gunakan jumlah ini: {json.dumps(conf)}.
        
        WAJIB OUTPUT JSON MURNI DALAM SATU LIST FLAT:
        {{ "soal_list": [ 
          {{ "tipe": "Nama Tipe Soal", "soal": "isi", "opsi": ["A","B","C","D"], "kunci": "A", "indikator": "...", "skor": 5, "level": "L2" }}
        ] }}"""

        with st.spinner("Menyusun data..."):
            res = model.generate_content(prompt)
            clean_res = clean_json_output(res.text)
            data = json.loads(clean_res)
            soal_list = data.get('soal_list', [])
            
            if not soal_list:
                st.error("AI tidak mengembalikan daftar soal. Coba lagi.")
                st.stop()

            st.session_state.preview_data = soal_list
            info_dict = {'sekolah': sekolah, 'mapel': mapel, 'kelas': kelas, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen, 'semester': 'Genap'}
            
            st.session_state.files = {
                'n': generate_naskah(soal_list, info_dict),
                'k': generate_kisi_kisi(soal_list, info_dict)
            }
            st.success("Berhasil!")
            
    except Exception as e:
        st.error(f"Error: {e}. Klik 'Proses Data' lagi.")

# --- 4. OUTPUT ---
if 'files' in st.session_state:
    st.divider()
    c1, c2 = st.columns(2)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    c1.download_button("📝 Unduh Naskah", to_io(st.session_state.files['n']), "Naskah_Soal.docx", "primary")
    c2.download_button("🔑 Unduh Kisi-kisi", to_io(st.session_state.files['k']), "Kisi_Kisi.docx")

    st.subheader("👁️ Preview")
    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} ({q.get('tipe')})"):
            st.write(q.get('soal'))
            st.caption(f"Kunci: {q.get('kunci')}")
