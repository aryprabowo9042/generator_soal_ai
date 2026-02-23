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

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah 1 Weleri", layout="wide")

# Custom CSS untuk gaya modern bertema Biru (Tailwind-like)
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Card Container */
    div.stButton > button {
        background-color: #2563eb;
        color: white;
        border-radius: 0.5rem;
        padding: 0.6rem 1.2rem;
        border: none;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }
    
    div.stButton > button:hover {
        background-color: #1d4ed8;
        border: none;
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Header Styling */
    h1, h2, h3 {
        color: #1e3a8a !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #ffffff;
        border-radius: 0.5rem !important;
        border: 1px solid #e2e8f0 !important;
        color: #2563eb !important;
    }

    /* Info & Success Boxes */
    .stAlert {
        border-radius: 0.75rem;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

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
        row[3].text = str(round(q.get('skor', 0), 2))
    return doc

# (Fungsi generate_kisi_kisi dan generate_kartu tetap sama seperti sebelumnya)
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
        tbl.cell(4, 0).text = "Skor"; tbl.cell(4, 1).text = str(round(q.get('skor', 0), 2))
        doc.add_paragraph()
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Muhammadiyah_Logo.svg/1200px-Muhammadiyah_Logo.svg.png", width=80)
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

# Judul dengan gaya modern
st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>📝 Generator Administrasi Soal AI</h1>", unsafe_allow_html=True)

with st.container():
    st.markdown("""<div style='background-color: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); border: 1px solid #e2e8f0;'>""", unsafe_allow_html=True)
    st.subheader("📖 Input Materi Asesmen")
    col_mat1, col_mat2 = st.columns(2)
    with col_mat1:
        materi_manual = st.text_area("Input Materi (Teks/Ringkasan)", placeholder="Ketik materi di sini...", height=200)
    with col_mat2:
        uploaded_file = st.file_uploader("Atau Unggah Materi (PDF)", type=['pdf'])
    st.markdown("</div>", unsafe_allow_html=True)

st.write("") # Spacer

col_sets1, col_sets2 = st.columns([2, 1])
with col_sets1:
    jenis_asesmen = st.selectbox("Peruntukan Soal", [
        "Asesmen Formatif", "Asesmen Sumatif Lingkup Materi",
        "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"
    ])
    bentuk_soal = st.multiselect("Bentuk Soal", 
        ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], 
        default=["Pilihan Ganda", "Uraian"])

with col_sets2:
    conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

st.write("")

if st.button("🚀 PROSES DATA DAN GENERATE SOAL"):
    if not api_key: 
        st.error("Masukkan API Key di Sidebar!"); st.stop()
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
        
        # PROMPT yang menginstruksikan pembagian skor otomatis agar total 100
        total_soal = sum(conf.values())
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. 
        Materi: {materi_full[:7000]}. 
        Jumlah soal: {json.dumps(conf)}.
        
        PENTING: Berikan nilai properti 'skor' untuk setiap soal sedemikian rupa sehingga jika dijumlahkan semuanya, total skor adalah tepat 100.
        Misal jika ada 20 soal, berikan masing-masing skor 5. Jika tingkat kesulitan berbeda (uraian), sesuaikan distribusinya.
        
        OUTPUT JSON MURNI: {{ "soal_list": [ {{ "tipe": "", "soal": "", "opsi": [], "kunci": "", "pedoman": "", "indikator": "", "skor": 0, "level": "" }} ] }}"""

        with st.spinner("AI sedang merancang soal dan administrasi..."):
            res = model.generate_content(prompt)
            raw_data = clean_json_output(res.text)
            data = json.loads(raw_data)
            soal_list = data.get('soal_list', [])
            
            # Normalisasi skor secara manual untuk memastikan TOTAL = 100
            current_total = sum(q.get('skor', 0) for q in soal_list)
            if current_total > 0:
                for q in soal_list:
                    q['skor'] = (q['skor'] / current_total) * 100

            st.session_state.preview_data = soal_list
            info_dict = {
                'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 
                'kelas': kelas, 'semester': semester, 'tahun': tahun, 
                'jenis_asesmen': jenis_asesmen
            }
            
            st.session_state.files = {
                'n': generate_naskah(soal_list, info_dict),
                'k': generate_kisi_kisi(soal_list, info_dict),
                's': generate_kartu(soal_list, info_dict),
                'kj': generate_kunci_pedoman(soal_list, info_dict)
            }
            st.success("🎉 Administrasi berhasil dibuat!")
            
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

# --- 4. OUTPUT ---
if 'files' in st.session_state and st.session_state.files:
    st.divider()
    st.markdown("### 📥 Unduh Dokumen Administrasi")
    c1, c2, c3, c4 = st.columns(4)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    with c1: st.download_button("📄 Naskah Soal", to_io(st.session_state.files['n']), "1_Naskah_Soal.docx")
    with c2: st.download_button("🔑 Kunci & Pedoman", to_io(st.session_state.files['kj']), "2_Kunci_Pedoman.docx")
    with c3: st.download_button("📋 Kisi-kisi Soal", to_io(st.session_state.files['k']), "3_Kisi_Kisi.docx")
    with c4: st.download_button("🗃️ Kartu Soal", to_io(st.session_state.files['s']), "4_Kartu_Soal.docx")

    st.write("")
    st.markdown("### 👁️ Preview Soal")
    
    total_skor_check = sum(q.get('skor', 0) for q in st.session_state.preview_data)
    st.info(f"Total Skor Kumulatif: **{round(total_skor_check, 0)}**")

    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} - {q.get('tipe')} (Skor: {round(q.get('skor',0), 1)})"):
            st.write(f"**Pertanyaan:**\n{q.get('soal')}")
            if q.get('opsi'):
                for idx, opt in enumerate(q.get('opsi')):
                    st.write(f"{['A','B','C','D','E'][idx]}. {opt}")
            st.markdown(f"**Kunci Jawaban:** `{q.get('kunci')}`")
            if q.get('pedoman'):
                st.caption(f"Pedoman: {q.get('pedoman')}")
