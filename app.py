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
    .stAlert { border-radius: 0.75rem; border: none; }
    /* Gaya Khusus Preview Arab */
    .arabic-text { font-family: 'Sakkal Majalla', 'Traditional Arabic', serif; direction: rtl; text-align: right; font-size: 22px; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILS UNTUK ARAB (RTL) ---
def set_rtl(paragraph):
    """Mengatur paragraf agar mendukung penulisan kanan-ke-kiri (RTL)"""
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
        run.font.size = Pt(size + 4) # Font arab biasanya butuh ukuran lebih besar
    else:
        run.font.name = 'Times New Roman'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        run.font.size = Pt(size)
    run.bold = bold

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets: return st.secrets["GEMINI_API_KEY"]
    return ""

def clean_json_output(text):
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        return text[start:end] if start != -1 else text
    except: return text

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
    is_arab = "arab" in info['mapel'].lower()
    
    no = 1
    grouped = {}
    for q in data_list:
        t = q.get('tipe', 'Soal')
        if t not in grouped: grouped[t] = []
        grouped[t].append(q)

    for tipe, quests in grouped.items():
        p_tipe = doc.add_paragraph()
        r_tipe = p_tipe.add_run(f"\n{tipe.upper()}")
        set_font(r_tipe, 11, True)
        
        for q in quests:
            p_soal = doc.add_paragraph()
            if is_arab: set_rtl(p_soal)
            
            # Gabungkan nomor dan pertanyaan
            run_no = p_soal.add_run(f"{no}. ")
            set_font(run_no, 11, is_arabic=False)
            run_text = p_soal.add_run(q.get('soal', ''))
            set_font(run_text, 12, is_arabic=is_arab)
            
            if "Pilihan Ganda" in tipe:
                opsi = q.get('opsi', [])
                labels = ['أ', 'ب', 'ج', 'د'] if is_arab else ['A', 'B', 'C', 'D']
                for i, o in enumerate(opsi[:4]):
                    p_opt = doc.add_paragraph()
                    if is_arab: set_rtl(p_opt)
                    run_opt = p_opt.add_run(f"    {labels[i]}. {o}")
                    set_font(run_opt, 11, is_arabic=is_arab)
            elif "Benar / Salah" in tipe:
                p_bs = doc.add_paragraph("    ....... ( ) Benar   ( ) Salah")
                if is_arab: set_rtl(p_bs)
            no += 1
    return doc

# (Fungsi generate_kunci_pedoman, generate_kisi_kisi, generate_kartu tetap sama tapi panggil set_font yang baru)

# --- 3. UI UTAMA ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Muhammadiyah_Logo.svg/1200px-Muhammadiyah_Logo.svg.png", width=80)
    st.header("⚙️ Konfigurasi")
    saved_api = get_api_key()
    api_key = st.text_input("Gemini API Key", value=saved_api, type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Nama Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Bahasa Arab") # Default Bahasa Arab
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal v6.0 (Arabic Support)")

with st.container():
    st.markdown("""<div style='background-color: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); border: 1px solid #e2e8f0;'>""", unsafe_allow_html=True)
    st.subheader("📖 Input Materi Asesmen")
    col_mat1, col_mat2 = st.columns(2)
    with col_mat1:
        materi_manual = st.text_area("Input Materi", placeholder="Ketik materi (Indonesia atau Arab)...", height=200)
    with col_mat2:
        uploaded_file = st.file_uploader("Atau Unggah PDF Materi", type=['pdf'])
    st.markdown("</div>", unsafe_allow_html=True)

st.write("") 

col_sets1, col_sets2 = st.columns([2, 1])
with col_sets1:
    jenis_asesmen = st.selectbox("Peruntukan Soal", ["Asesmen Formatif", "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester", "Asesmen Sumatif Akhir Semester"])
    bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar / Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
with col_sets2:
    conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA DAN GENERATE SOAL"):
    if not api_key: st.error("Masukkan API Key di Sidebar!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        materi_full = materi_manual + " "
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_full += " ".join([p.extract_text() for p in reader.pages])

        model = genai.GenerativeModel('gemini-1.5-flash')
        
        is_arab = "arab" in mapel.lower()
        lang_instruction = "Gunakan Bahasa Arab berharakat lengkap untuk bagian soal dan opsi." if is_arab else "Gunakan Bahasa Indonesia yang baik dan benar."
        
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. 
        Materi: {materi_full[:7000]}. 
        Jumlah soal: {json.dumps(conf)}.
        {lang_instruction}
        
        PENTING: Total skor harus tepat 100.
        OUTPUT JSON MURNI: {{ "soal_list": [ {{ "tipe": "", "soal": "", "opsi": [], "kunci": "", "pedoman": "", "indikator": "", "skor": 0, "level": "" }} ] }}"""

        with st.spinner("AI sedang merancang soal Bahasa Arab..."):
            res = model.generate_content(prompt)
            data = json.loads(clean_json_output(res.text))
            soal_list = data.get('soal_list', [])
            
            # Normalisasi skor
            current_total = sum(q.get('skor', 0) for q in soal_list)
            if current_total > 0:
                for q in soal_list: q['skor'] = (q['skor'] / current_total) * 100

            st.session_state.preview_data = soal_list
            info_dict = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            
            st.session_state.files = {
                'n': generate_naskah(soal_list, info_dict),
                'kj': generate_kunci_pedoman(soal_list, info_dict),
                'k': generate_kisi_kisi(soal_list, info_dict),
                's': generate_kartu(soal_list, info_dict)
            }
            st.success("🎉 Administrasi berhasil dibuat!")
            
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

# --- 4. OUTPUT ---
if 'files' in st.session_state:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    c1.download_button("📄 Naskah Soal", to_io(st.session_state.files['n']), "Naskah_Soal.docx")
    c2.download_button("🔑 Kunci & Pedoman", to_io(st.session_state.files['kj']), "Kunci_Pedoman.docx")
    c3.download_button("📋 Kisi-kisi", to_io(st.session_state.files['k']), "Kisi_Kisi.docx")
    c4.download_button("🗂️ Kartu Soal", to_io(st.session_state.files['s']), "Kartu_Soal.docx")

    st.markdown("### 👁️ Preview Soal")
    is_arab = "arab" in mapel.lower()
    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} - {q.get('tipe')}"):
            if is_arab:
                st.markdown(f"<div class='arabic-text'>{q.get('soal')}</div>", unsafe_allow_html=True)
                if q.get('opsi'):
                    for idx, opt in enumerate(q.get('opsi')):
                        st.markdown(f"<div class='arabic-text'>{['أ','ب','ج','د'][idx]}. {opt}</div>", unsafe_allow_html=True)
            else:
                st.write(q.get('soal'))
                if q.get('opsi'):
                    for idx, opt in enumerate(q.get('opsi')):
                        st.write(f"{['A','B','C','D'][idx]}. {opt}")
            st.info(f"Kunci: {q.get('kunci')}")
