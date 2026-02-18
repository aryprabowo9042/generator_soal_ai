import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import json
import re

# --- 1. SETTINGS & UTILITIES ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def t(value):
    return str(value) if value is not None else ""

def set_font(run, size=11, bold=False, font_name='Times New Roman'):
    try:
        run.font.name = font_name
        if not font_name == 'Times New Roman': 
            run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
        run.font.size = Pt(int(size))
        run.bold = bold
    except:
        pass

def clean_option(opt):
    """Menghapus prefix A. B. C. jika AI membuatnya dobel"""
    return re.sub(r'^[A-E][.\s]+', '', str(opt)).strip()

def remove_table_borders(table):
    """Menghilangkan garis tabel untuk opsi PG horizontal"""
    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._element.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for border in ['top', 'left', 'bottom', 'right']:
                element = OxmlElement(f'w:{border}')
                element.set(qn('w:val'), 'nil')
                tcBorders.append(element)
            tcPr.append(tcBorders)

# --- 2. DOKUMEN GENERATORS ---

def generate_docs_final(data_soal, info_sekolah, info_ujian):
    # --- DOKUMEN 1: NASKAH SOAL ---
    d1 = Document()
    p = d1.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {t(info_sekolah['cabang'])}\n"); set_font(r, 12, True)
    r = p.add_run(f"{t(info_sekolah['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info_ujian['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info_sekolah['tahun'])}"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    tbl = d1.add_table(2, 2); tbl.autofit = True
    c = tbl.rows[0].cells
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {t(info_ujian['mapel'])}"); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"WAKTU : {t(info_ujian['waktu'])} menit"); set_font(r, 10)
    c = tbl.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"KELAS : {t(info_ujian['kelas'])}"); set_font(r, 10)
    d1.add_paragraph()
    
    no = 1
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        quests = data_soal.get(tipe, [])
        if not quests: continue
        p = d1.add_paragraph()
        if tipe == "Pilihan Ganda":
            r = p.add_run("A. Pilihan Ganda\n"); set_font(r, 12, True)
            r = p.add_run("Berilah tanda silang (x) pada A, B, C atau D pada jawaban yang paling benar!"); set_font(r, 11)
        elif tipe == "Benar Salah":
            r = p.add_run("B. Benar / Salah\n"); set_font(r, 12, True)
            r = p.add_run("Tentukan apakah pernyataan tersebut Benar (B) atau Salah (S)."); set_font(r, 11)
        else:
            r = p.add_run("C. Uraian\n"); set_font(r, 12, True)
            r = p.add_run("Jawablah pertanyaan-pertanyaan berikut ini dengan cermat dan lengkap!"); set_font(r, 11)

        if tipe == "Benar Salah":
            bs_tbl = d1.add_table(1, 4); bs_tbl.style = 'Table Grid'
            h = bs_tbl.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests:
                row = bs_tbl.add_row().cells
                row[0].text = t(no); row[1].text = t(q.get('soal', '-'))
                no += 1
        else:
            for q in quests:
                d1.add_paragraph(f"{t(no)}. {t(q.get('soal', '-'))}")
                if tipe == "Pilihan Ganda" and 'opsi' in q:
                    opt_tbl = d1.add_table(1, 4)
                    remove_table_borders(opt_tbl)
                    lbl = ['A','B','C','D']
                    for i, o in enumerate(q['opsi'][:4]):
                        r = opt_tbl.rows[0].cells[i].paragraphs[0].add_run(f"{lbl[i]}. {clean_option(o)}")
                        set_font(r, 11)
                no += 1

    # --- DOKUMEN 2: KARTU SOAL ---
    d2 = Document()
    count = 1
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        for q in data_soal.get(tipe, []):
            kt = d2.add_table(6, 2); kt.style = 'Table Grid'
            rows = [("Nomor Soal", t(count)), ("TP", t(q.get('tp'))), ("Indikator", t(q.get('indikator'))), 
                    ("Level", t(q.get('level'))), ("Soal", t(q.get('soal'))), ("Kunci", t(q.get('kunci', q.get('skor'))))]
            for i, (l, v) in enumerate(rows):
                kt.cell(i, 0).text = l; kt.cell(i, 1).text = v
            d2.add_paragraph(); count += 1

    # --- DOKUMEN 3: KISI-KISI ---
    d3 = Document()
    ks = d3.add_table(1, 6); ks.style = 'Table Grid'
    for i, h in enumerate(["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]): ks.cell(0, i).text = h
    count = 1
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        for q in data_soal.get(tipe, []):
            row = ks.add_row().cells
            for i, v in enumerate([t(count), t(q.get('tp')), t(q.get('indikator')), t(q.get('level')), tipe, t(count)]):
                row[i].text = v
            count += 1
            
    return d1, d2, d3

# --- 3. UI STREAMLIT ---
if 'files' not in st.session_state: st.session_state.files = None

st.title("✅ Generator Soal SMP Muhammadiyah")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    if st.button("🔄 Reset Aplikasi"):
        st.session_state.files = None
        st.rerun()

c1, c2 = st.columns(2)
sekolah = c1.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
guru = c1.text_input("Guru Pengampu", "Ary Prabowo")
mapel = c2.text_input("Mata Pelajaran", "Seni Budaya")
kelas = c2.text_input("Kelas", "IX / Genap")
jenis = st.selectbox("Asesmen", ["ATS", "AAS", "Sumatif"])

# PENGATURAN SOAL (DIKEMBALIKAN)
st.subheader("📊 Pengaturan Soal")
opsi_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {k: st.number_input(f"Jumlah {k}", 1, 40, 5) for k in opsi_soal}

materi = st.text_area("Materi/Kisi-kisi (Paste di sini)", height=200)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("API Key dan Materi tidak boleh kosong!")
    else:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            m_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
            
            model = genai.GenerativeModel(m_name)
            prompt = f"""
            Buat soal JSON dari materi: {materi}. Jumlah: {json.dumps(conf)}.
            Format: {{ "Pilihan Ganda": [{{ "tp": "..", "indikator": "..", "level": "L1/L2/L3", "soal": "..", "opsi": [".."], "kunci": ".." }}], ... }}
            Output HANYA JSON.
            """
            
            with st.spinner(f"AI sedang bekerja (Model: {m_name})..."):
                res = model.generate_content(prompt)
                data = json.loads(re.sub(r'```json|```', '', res.text).strip())
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': 90, 'jenis_asesmen': jenis, 'guru': guru}
                
                d1, d2, d3 = generate_docs_final(data, info_s, info_u)
                
                def b(d): 
                    io = BytesIO(); d.save(io); return io.getvalue()
                
                st.session_state.files = {'n': b(d1), 'k': b(d2), 's': b(d3)}
                st.success("Berhasil! Silakan unduh di bawah.")
        except Exception as e:
            st.error(f"Kesalahan: {e}")

if st.session_state.files:
    st.divider()
    cl1, cl2, cl3 = st.columns(3)
    cl1.download_button("📥 Naskah Soal", st.session_state.files['n'], f"Naskah_{mapel}.docx")
    cl2.download_button("📥 Kartu Soal", st.session_state.files['k'], f"Kartu_{mapel}.docx")
    cl3.download_button("📥 Kisi-Kisi", st.session_state.files['s'], f"Kisi_{mapel}.docx")
