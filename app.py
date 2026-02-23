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

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return ""

def clean_json_output(text):
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        return text[start:end] if start != -1 else text
    except:
        return text

def clean_option(opt):
    if not opt: return ""
    text = str(opt)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS ---

def create_header(doc, info, title_suffix=""):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info['jenis_asesmen'].upper()} {title_suffix}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(2, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']} / {info['semester']}")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

def generate_naskah(data_list, info):
    doc = Document(); create_header(doc, info)
    grouped = {}
    for q in data_list:
        t = q.get('tipe', 'Soal')
        if t not in grouped: grouped[t] = []
        grouped[t].append(q)
    
    no = 1
    for tipe, quests in grouped.items():
        p_tipe = doc.add_paragraph()
        r_tipe = p_tipe.add_run(f"\n{tipe.upper()}")
        set_font(r_tipe, 11, True)
        for q in quests:
            p_soal = doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in tipe:
                opsi = q.get('opsi', [])
                for i, o in enumerate(opsi[:4]):
                    doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            elif "Benar / Salah" in tipe:
                doc.add_paragraph("    ....... ( ) Benar   ( ) Salah")
            no += 1
    return doc

def generate_kunci_pedoman(data_list, info):
    doc = Document(); create_header(doc, info, "- KUNCI JAWABAN & PEDOMAN")
    table = doc.add_table(1, 4); table.style = 'Table Grid'
    hd = ["No", "Tipe", "Kunci Jawaban / Pedoman", "Skor"]
    for i, h in enumerate(hd): table.rows[0].cells[i].text = h
    
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1)
        row[1].text = q.get('tipe', '-')
        kunci = q.get('kunci', '')
        pedoman = q.get('pedoman', '')
        row[2].text = f"Kunci: {kunci}\nPedoman: {pedoman}" if pedoman else str(kunci)
        row[3].text = str(q.get('skor', 0))
    return doc

def generate_kisi_kisi(data_list, info):
    doc = Document()
    doc.add_heading(f"KISI-KISI SOAL {info['jenis_asesmen']}", 1)
    p = doc.add_paragraph()
    p.add_run(f"Guru Mapel: {info['guru']}\nMapel: {info['mapel']}\nKelas/Semester: {info['kelas']}/{info['semester']}")
    
    table = doc.add_table(1, 6); table.style = 'Table Grid'
    hd = ["No", "TP/KD", "Indikator Soal", "Level", "Bentuk Soal", "No Soal"]
    for i, h in enumerate(hd): table.rows[0].cells[i].text = h
    
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1)
        row[2].text = q.get('indikator', '-')
        row[3].text = q.get('level', 'L2')
        row[4].text = q.get('tipe', '-')
        row[5].text = str(i+1)
    return doc

def generate_kartu(data_list, info):
    doc = Document()
    doc.add_heading(f"KARTU SOAL - {info['guru']}", 1)
    for i, q in enumerate(data_list):
        tbl = doc.add_table(5, 2); tbl.style = 'Table Grid'
        tbl.cell(0, 0).text = "Nomor Soal"; tbl.cell(0, 1).text = str(i+1)
        tbl.cell(1, 0).text = "Indikator"; tbl.cell(1, 1).text = q.get('indikator', '-')
        tbl.cell(2, 0).text = "Butir Soal"; tbl.cell(2, 1).text = q.get('soal', '')
        tbl.cell(3, 0).text = "Kunci/Pedoman"; tbl.cell(3, 1).text = f"{q.get('kunci', '-')} \nPedoman: {q.get('pedoman','')}"
        tbl.cell(4, 0).text = "Skor"; tbl.cell(4, 1).text = str(q.get('skor', 5))
        doc.add_paragraph()
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    saved_api = get_api_key()
    api_key = st.text_input("Gemini API Key", value=saved_api, type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Nama Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal v5.4.1")

st.subheader("📖 Input Materi Asesmen")
col_mat1, col_mat2 = st.columns(2)
with col_mat1:
    materi_manual = st.text_area("Input Materi (Teks/Ringkasan)", placeholder="Ketik materi di sini...", height=200)
with col_mat2:
    uploaded_file = st.file_uploader("Atau Unggah Materi (PDF)", type=['pdf'])

st.divider()
jenis_asesmen = st.selectbox("Peruntukan Soal", [
    "Asesmen Formatif", "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"
])

bentuk_soal = st.multiselect("Bentuk Soal", 
    ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], 
    default=["Pilihan Ganda", "Uraian"])

conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: 
        st.error("Masukkan API Key!"); st.stop()
    if not materi_manual and not uploaded_file:
        st.warning("Mohon masukkan materi!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        m_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        active_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in m_models else m_models[0]
        
        materi_full = materi_manual + " "
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_full += " ".join([p.extract_text() for p in reader.pages])

        model = genai.GenerativeModel(active_model)
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. 
        Materi: {materi_full[:7000]}. Jumlah: {json.dumps(conf)}. 
        OUTPUT JSON MURNI: {{ "soal_list": [ {{ "tipe": "", "soal": "", "opsi": [], "kunci": "", "pedoman": "", "indikator": "", "skor": 5, "level": "" }} ] }}"""

        with st.spinner("AI sedang bekerja..."):
            res = model.generate_content(prompt)
            raw_data = clean_json_output(res.text)
            data = json.loads(raw_data)
            soal_list = data.get('soal_list', [])
            
            if not soal_list:
                st.error("AI gagal menghasilkan soal. Coba lagi.")
            else:
                st.session_state.preview_data = soal_list
                info_dict = {
                    'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 
                    'kelas': kelas, 'semester': semester, 'tahun': tahun, 
                    'jenis_asesmen': jenis_asesmen
                }
                
                # Simpan ke session state
                st.session_state.files = {
                    'n': generate_naskah(soal_list, info_dict),
                    'k': generate_kisi_kisi(soal_list, info_dict),
                    's': generate_kartu(soal_list, info_dict),
                    'kj': generate_kunci_pedoman(soal_list, info_dict)
                }
                st.success("Berhasil! Silakan unduh dokumen di bawah.")
            
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

# --- 4. OUTPUT (SANGAT PENTING: Pengecekan 'if') ---
if 'files' in st.session_state and st.session_state.files:
    st.divider()
    # Pastikan kunci 'kj' ada sebelum membuat tombol
    if 'kj' in st.session_state.files:
        c1, c2, c3, c4 = st.columns(4)
        def to_io(doc):
            io = BytesIO(); doc.save(io); return io.getvalue()

        c1.download_button("📝 Naskah", to_io(st.session_state.files['n']), "Naskah_Soal.docx", "primary")
        c2.download_button("🔑 Kunci & Pedoman", to_io(st.session_state.files['kj']), "Kunci_Jawaban.docx")
        c3.download_button("📖 Kisi-kisi", to_io(st.session_state.files['k']), "Kisi_Kisi.docx")
        c4.download_button("🗂️ Kartu Soal", to_io(st.session_state.files['s']), "Kartu_Soal.docx")

    st.subheader("👁️ Preview Soal")
    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} - {q.get('tipe')}"):
            st.write(q.get('soal'))
            st.caption(f"Kunci: {q.get('kunci')}")
