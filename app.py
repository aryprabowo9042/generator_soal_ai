import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- 1. SETUP & FUNGSI PENGAMAN ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def t(value):
    return str(value) if value is not None else ""

# --- FUNGSI FONT (SINKRON & STABIL) ---
def set_font(run, size=12, bold=False, font_name='Times New Roman'):
    """Fungsi ini sekarang mendukung positional dan keyword arguments."""
    try:
        run.font.name = font_name
        run.font.size = Pt(int(size))
        run.bold = bold
    except:
        pass

# --- 2. GENERATOR DOKUMEN ---
def generate_docs_final(data_soal, info_sekolah, info_ujian):
    d1 = Document()
    
    # Header
    p = d1.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 10, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {t(info_sekolah['cabang'])}\n"); set_font(r, 11, True)
    r = p.add_run(f"{t(info_sekolah['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info_ujian['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info_sekolah['tahun'])}"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    # Identitas
    tbl = d1.add_table(2, 2); tbl.autofit = True
    c = tbl.rows[0].cells
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {t(info_ujian['mapel'])}"); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"WAKTU : {t(info_ujian['waktu'])} menit"); set_font(r, 10)
    c = tbl.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"KELAS : {t(info_ujian['kelas'])}"); set_font(r, 10)
    d1.add_paragraph()
    
    headers = {
        "Pilihan Ganda": "Pilihan Ganda\nSilanglah (x) jawaban yang benar!", 
        "Uraian": "Uraian\nJawablah dengan jelas!", 
        "Benar Salah": "Benar / Salah", 
        "Isian Singkat": "Isian Singkat"
    }
    abjad = ['A','B','C','D','E']
    idx = 0; no = 1
    
    for tipe, quests in data_soal.items():
        if not quests: continue
        p = d1.add_paragraph()
        judul = headers.get(tipe, tipe)
        # Panggilan bold=True di bawah ini sekarang aman:
        r = p.add_run(f"\n{abjad[idx]}. {t(judul)}"); set_font(r, bold=True)
        
        if tipe == "Benar Salah":
            sub_tbl = d1.add_table(1, 4); sub_tbl.style = 'Table Grid'
            h = sub_tbl.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests:
                row = sub_tbl.add_row().cells
                row[0].text = t(no); row[1].text = t(q.get('soal', '-'))
                no += 1
        else:
            for q in quests:
                d1.add_paragraph(f"{t(no)}. {t(q.get('soal', '-'))}")
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p_opsi = d1.add_paragraph(); p_opsi.paragraph_format.left_indent = Inches(0.3)
                    lbl = ['A','B','C','D']
                    for i, o in enumerate(q['opsi']):
                        if i < 4: p_opsi.add_run(f"{lbl[i]}. {t(o)}    ")
                no += 1
        idx += 1

    # DOKUMEN 2: KARTU SOAL
    d2 = Document()
    p = d2.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL\n{t(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        for q in quests:
            kartu_tbl = d2.add_table(6, 2); kartu_tbl.style = 'Table Grid'
            kunci = q.get('kunci', '-') if tipe != 'Uraian' else q.get('skor', '-')
            rows = [("No Soal", t(no)), ("TP", t(q.get('tp', '-'))), ("Indikator", t(q.get('indikator', '-'))), 
                    ("Level", t(q.get('level', '-'))), ("Butir Soal", t(q.get('soal', '-'))), ("Kunci/Skor", t(kunci))]
            for i, (lab, val) in enumerate(rows):
                kartu_tbl.cell(i, 0).text = lab
                kartu_tbl.cell(i, 1).text = val
            d2.add_paragraph(); no += 1

    # DOKUMEN 3: KISI-KISI
    d3 = Document()
    p = d3.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KISI-KISI SOAL\n{t(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    
    kisi_tbl = d3.add_table(1, 6); kisi_tbl.style = 'Table Grid'
    for i, h in enumerate(["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]): kisi_tbl.cell(0, i).text = h
    
    no = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            row = kisi_tbl.add_row().cells
            row[0].text = t(no); row[1].text = t(q.get('tp', '-'))
            row[2].text = t(q.get('indikator', '-')); row[3].text = t(q.get('level', '-'))
            row[4].text = t(tipe); row[5].text = t(no)
            no += 1
            
    return d1, d2, d3

# --- 3. UI STREAMLIT ---
st.title("🚀 Generator Soal Muhammadiyah")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "................")
    nbm = st.text_input("NBM", ".......")

c1, c2 = st.columns(2)
mapel = c1.text_input("Mapel", "IPA")
kelas = c1.text_input("Kelas", "VII / Genap")
waktu = c2.number_input("Waktu", 90)
jenis = c2.selectbox("Jenis", ["Sumatif Lingkup Materi", "ATS", "AAS"])

opsi = st.multiselect("Bentuk", ["Pilihan Ganda", "Uraian", "Benar Salah", "Isian Singkat"], default=["Pilihan Ganda"])
conf = {k: st.number_input(f"Jml {k}", 1, 30, 5) for k in opsi}
materi = st.text_area("Materi/Kisi-kisi:")

if st.button("PROSES SEKARANG"):
    if api_key and materi:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"Buat soal JSON dari materi ini: {materi}. Bentuk: {json.dumps(conf)}. Format JSON harus memiliki key: tp, indikator, level, soal, opsi (khusus PG), kunci/skor. HANYA JSON."
            
            with st.spinner("Menyusun soal..."):
                res = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(txt)
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
                
                d1, d2, d3 = generate_docs_final(data, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                col1, col2, col3 = st.columns(3)
                col1.download_button("📥 Naskah Soal", b(d1), "Naskah_Soal.docx")
                col2.download_button("📥 Kartu Soal", b(d2), "Kartu_Soal.docx")
                col3.download_button("📥 Kisi-Kisi", b(d3), "Kisi_Kisi.docx")
                st.success("Selesai! Silakan unduh file di atas.")
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
    else:
        st.warning("Isi API Key dan Materi dulu ya!")
