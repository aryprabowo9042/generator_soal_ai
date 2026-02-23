import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import json
import re
import PyPDF2

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah 1 Weleri", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    div.stButton > button {
        background-color: #2563eb; color: white; border-radius: 0.5rem;
        padding: 0.6rem 1.2rem; border: none; font-weight: 600; transition: all 0.2s; width: 100%;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8; transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Inter', sans-serif; }
    .arabic-preview {
        font-family: 'Traditional Arabic', serif;
        direction: rtl; text-align: right; font-size: 24px; line-height: 1.8;
        padding: 15px; background-color: #ffffff; border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI AMBIL API KEY DARI SECRETS ---
def get_api_key():
    # Mengambil GEMINI_API_KEY yang sudah Anda setting di dashboard Streamlit
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return ""

# --- UTILS RTL & FONT ---
def set_rtl(paragraph):
    pPr = paragraph._element.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

def set_font(run, size=11, bold=False, is_arabic=False):
    if is_arabic:
        run.font.name = 'Traditional Arabic'
        run._element.rPr.rFonts.set(qn('w:ascii'), 'Traditional Arabic')
        run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Traditional Arabic')
        run._element.rPr.rFonts.set(qn('w:cs'), 'Traditional Arabic')
        run.font.size = Pt(size + 5)
    else:
        run.font.name = 'Times New Roman'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        run.font.size = Pt(size)
    run.bold = bold

def clean_json_output(text):
    try:
        text = re.sub(r'```json\s*|\s*```', '', text)
        start = text.find('{')
        end = text.rfind('}') + 1
        return text[start:end] if start != -1 else text
    except: return text

def clean_option(opt):
    if not opt: return ""
    text = str(opt)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

# --- 2. DOKUMEN GENERATORS ---
def create_header(doc, info, title_suffix=""):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info['jenis_asesmen'].upper()} {title_suffix}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(3, 2)
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']} / {info['semester']}"),
        (f"GURU PENGAMPU : {info['guru']}", "")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

def generate_naskah(data_list, info):
    doc = Document(); create_header(doc, info)
    is_arab = "arab" in info['mapel'].lower()
    grouped = {}
    for q in data_list:
        t = q.get('tipe', 'Soal')
        if t not in grouped: grouped[t] = []
        grouped[t].append(q)
    
    no = 1
    for tipe, quests in grouped.items():
        p_tipe = doc.add_paragraph()
        r_tipe = p_tipe.add_run(f"\n{tipe.upper()}"); set_font(r_tipe, 11, True)
        for q in quests:
            p_soal = doc.add_paragraph()
            if is_arab: set_rtl(p_soal)
            run_no = p_soal.add_run(f"{no}. "); set_font(run_no, 11)
            run_text = p_soal.add_run(q.get('soal', '')); set_font(run_text, 12, is_arabic=is_arab)
            if "Pilihan Ganda" in tipe:
                opsi = q.get('opsi', [])
                labels = ['أ', 'ب', 'ج', 'د'] if is_arab else ['A', 'B', 'C', 'D']
                for i, o in enumerate(opsi[:4]):
                    p_opt = doc.add_paragraph()
                    if is_arab: set_rtl(p_opt)
                    run_opt = p_opt.add_run(f"    {labels[i]}. {clean_option(o)}"); set_font(run_opt, 11, is_arabic=is_arab)
            elif "Benar / Salah" in tipe:
                p_bs = doc.add_paragraph("    ....... ( ) Benar   ( ) Salah")
                if is_arab: set_rtl(p_bs)
            elif "Isian Singkat" in tipe:
                p_isi = doc.add_paragraph("    Jawaban: ...........................................")
                if is_arab: set_rtl(p_isi)
            no += 1
    return doc

def generate_kunci_pedoman(data_list, info):
    doc = Document(); create_header(doc, info, "- KUNCI JAWABAN & PEDOMAN")
    is_arab = "arab" in info['mapel'].lower()
    table = doc.add_table(1, 4); table.style = 'Table Grid'
    hd = ["No", "Tipe", "Kunci Jawaban / Pedoman", "Skor"]
    for i, h in enumerate(hd): table.rows[0].cells[i].text = h
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1); row[1].text = q.get('tipe', '-')
        p_kunci = row[2].paragraphs[0]
        if is_arab: set_rtl(p_kunci)
        kunci = q.get('kunci', ''); pedoman = q.get('pedoman', '')
        text = f"Kunci: {kunci}\nPedoman: {pedoman}" if pedoman else str(kunci)
        run_kunci = p_kunci.add_run(text); set_font(run_kunci, 10, is_arabic=is_arab)
        row[3].text = str(round(q.get('skor', 2), 2))
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
        row[0].text = str(i+1); row[1].text = q.get('tp', '-'); row[2].text = q.get('indikator', '-'); row[3].text = q.get('level', 'L2'); row[4].text = q.get('tipe', '-'); row[5].text = str(i+1)
    return doc

def generate_kartu(data_list, info):
    doc = Document()
    is_arab = "arab" in info['mapel'].lower()
    for i, q in enumerate(data_list):
        doc.add_heading(f"KARTU SOAL - {info['guru']}", 1)
        tbl = doc.add_table(5, 2); tbl.style = 'Table Grid'
        cells = [("Nomor Soal", str(i+1)), ("Indikator", q.get('indikator', '-')), ("Butir Soal", q.get('soal', '')), ("Kunci/Pedoman", f"{q.get('kunci', '-')} \nPedoman: {q.get('pedoman','')}") , ("Skor", str(round(q.get('skor', 0), 2)))]
        for idx, (label, val) in enumerate(cells):
            tbl.cell(idx, 0).text = label
            p = tbl.cell(idx, 1).paragraphs[0]
            if is_arab and idx in [2, 3]: set_rtl(p)
            run = p.add_run(str(val)); set_font(run, 11, is_arabic=(is_arab and idx in [2, 3]))
        doc.add_page_break()
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Muhammadiyah_Logo.svg/1200px-Muhammadiyah_Logo.svg.png", width=80)
    st.header("⚙️ Konfigurasi")
    
    # Otomatis deteksi API Key dari dashboard
    api_key_status = "✅ API Key Terdeteksi (Secrets)" if get_api_key() else "❌ API Key Belum Terdeteksi"
    st.info(api_key_status)

    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Nama Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Bahasa Arab")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.markdown("<h1 style='text-align: center;'>📝 Generator Administrasi Soal AI</h1>", unsafe_allow_html=True)

with st.container():
    st.markdown("""<div style='background-color: white; padding: 2rem; border-radius: 1rem; border: 1px solid #e2e8f0;'>""", unsafe_allow_html=True)
    st.subheader("📖 Input Materi Asesmen")
    col_mat1, col_mat2 = st.columns(2)
    with col_mat1: materi_manual = st.text_area("Input Materi (Teks/Ringkasan)", height=200, placeholder="Tempel materi di sini...")
    with col_mat2: uploaded_file = st.file_uploader("Atau Unggah PDF", type=['pdf'])
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
col_sets1, col_sets2 = st.columns([2, 1])
with col_sets1:
    jenis_asesmen = st.selectbox("Peruntukan Soal", ["Asesmen Formatif", "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"])
    bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
with col_sets2:
    conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 GENERATE SEKARANG"):
    api_key = get_api_key()
    if not api_key: st.error("API Key tidak ditemukan di Secrets!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        materi_full = materi_manual + " "
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_full += " ".join([p.extract_text() for p in reader.pages])

        is_arab = "arab" in mapel.lower()
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi_full[:7000]}. Jumlah: {json.dumps(conf)}.
        PENTING: {'GUNAKAN BAHASA ARAB BERHARAKAT LENGKAP untuk soal dan opsi.' if is_arab else ''}
        Aturan: 1. Total skor harus tepat 100. 2. Berikan 'tp', 'indikator', 'skor', 'level'.
        OUTPUT JSON MURNI: {{ "soal_list": [ {{ "tipe": "", "soal": "", "opsi": [], "kunci": "", "pedoman": "", "indikator": "", "tp": "", "skor": 0, "level": "" }} ] }}"""

        with st.spinner("AI sedang menyusun administrasi soal..."):
            res = model.generate_content(prompt)
            data = json.loads(clean_json_output(res.text))
            soal_list = data.get('soal_list', [])
            
            # Normalisasi skor agar pas 100
            total = sum(q.get('skor', 0) for q in soal_list)
            if total > 0:
                for q in soal_list: q['skor'] = (q['skor'] / total) * 100
                
            info = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            st.session_state.preview_data = soal_list
            st.session_state.files = {'n': generate_naskah(soal_list, info), 'k': generate_kisi_kisi(soal_list, info), 's': generate_kartu(soal_list, info), 'kj': generate_kunci_pedoman(soal_list, info)}
            st.success("🎉 Administrasi berhasil dibuat!")
    except Exception as e:
        st.error(f"Terjadi kesalahan teknis: {e}")

# --- 4. OUTPUT ---
if 'files' in st.session_state:
    st.divider()
    st.markdown("### 📥 Unduh Dokumen Administrasi")
    c1, c2, c3, c4 = st.columns(4)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()
    with c1: st.download_button("📄 Naskah Soal", to_io(st.session_state.files['n']), "1_Naskah_Soal.docx")
    with c2: st.download_button("🔑 Kunci Jawaban", to_io(st.session_state.files['kj']), "2_Kunci_Pedoman.docx")
    with c3: st.download_button("📋 Kisi-kisi", to_io(st.session_state.files['k']), "3_Kisi_Kisi.docx")
    with c4: st.download_button("🗃️ Kartu Soal", to_io(st.session_state.files['s']), "4_Kartu_Soal.docx")

    st.subheader("👁️ Preview Soal")
    is_arab = "arab" in mapel.lower()
    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} - {q.get('tipe')} (Skor: {round(q.get('skor',0), 1)})"):
            if is_arab:
                st.markdown(f"<div class='arabic-preview'>{q['soal']}</div>", unsafe_allow_html=True)
                if q.get('opsi'):
                    for idx, opt in enumerate(q.get('opsi')):
                        st.markdown(f"<div class='arabic-preview'>{['أ','ب','ج','د'][idx]}. {opt}</div>", unsafe_allow_html=True)
            else:
                st.write(q['soal'])
                if q.get('opsi'):
                    for idx, opt in enumerate(q.get('opsi')):
                        st.write(f"{['A','B','C','D'][idx]}. {opt}")
            st.info(f"Kunci Jawaban: {q.get('kunci')}")
