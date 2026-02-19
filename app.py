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
import pandas as pd

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
    return re.sub(r'^[A-E][.\s]+', '', str(opt)).strip()

def remove_table_borders(table):
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
    r = p.add_run(f"{t(info_sekolah['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"NASKAH SOAL {t(info_ujian['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"Mata Pelajaran: {t(info_ujian['mapel'])} | Kelas: {t(info_ujian['kelas'])}"); set_font(r, 11)
    d1.add_paragraph("_" * 75)
    
    no = 1
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        quests = data_soal.get(tipe, [])
        if not quests: continue
        d1.add_paragraph().add_run(f"\n{tipe}").bold = True
        for q in quests:
            d1.add_paragraph(f"{no}. {q.get('soal')}")
            if tipe == "Pilihan Ganda":
                opt_tbl = d1.add_table(1, 4)
                remove_table_borders(opt_tbl)
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    r = opt_tbl.rows[0].cells[i].paragraphs[0].add_run(f"{['A','B','C','D'][i]}. {clean_option(o)}")
                    set_font(r, 10)
            no += 1

    # --- DOKUMEN 2: KUNCI JAWABAN & PEDOMAN (FITUR BARU UNTUK CETAK) ---
    d_kunci = Document()
    p = d_kunci.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KUNCI JAWABAN & PEDOMAN PENSKORAN\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info_ujian['mapel'])} - {t(info_ujian['jenis_asesmen'])}\n"); set_font(r, 12)
    
    ktbl = d_kunci.add_table(1, 4); ktbl.style = 'Table Grid'
    hdr = ktbl.rows[0].cells
    hdr[0].text = 'No'; hdr[1].text = 'Bentuk'; hdr[2].text = 'Kunci / Pedoman Jawaban'; hdr[3].text = 'Skor'
    
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            row = ktbl.add_row().cells
            row[0].text = str(idx)
            row[1].text = tipe
            row[2].text = t(q.get('kunci') if tipe != "Uraian" else q.get('pedoman'))
            row[3].text = str(q.get('skor', 0))
            idx += 1

    # --- DOKUMEN 3: KISI-KISI ---
    d_kisi = Document()
    d_kisi.add_heading('KISI-KISI SOAL', 0)
    ks = d_kisi.add_table(1, 5); ks.style = 'Table Grid'
    for i, h in enumerate(["No", "Indikator", "Level", "Bentuk", "No Soal"]): ks.cell(0, i).text = h
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            r = ks.add_row().cells
            for i, v in enumerate([str(idx), t(q.get('indikator')), t(q.get('level')), tipe, str(idx)]):
                r[i].text = v
            idx += 1
            
    return d1, d_kunci, d_kisi

# --- 3. UI STREAMLIT ---
if 'files' not in st.session_state: st.session_state.files = None
if 'preview_data' not in st.session_state: st.session_state.preview_data = None

st.title("✅ Generator Soal & Kunci Jawaban v2")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    if st.button("🔄 Reset"):
        st.session_state.clear()
        st.rerun()

c1, c2 = st.columns(2)
sekolah = c1.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
mapel = c2.text_input("Mata Pelajaran", "Seni Budaya")
jenis = st.selectbox("Asesmen", ["ATS", "AAS", "Sumatif"])

st.subheader("📊 Konfigurasi")
opsi_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {k: st.number_input(f"Jumlah {k}", 1, 40, 5) for k in opsi_soal}
materi = st.text_area("Masukkan Materi/Kisi-kisi", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("Data belum lengkap!")
    else:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel('gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0])
            
            prompt = f"""
            Buat soal dari: {materi}. Jumlah: {json.dumps(conf)}.
            WAJIB TOTAL SKOR = 100.
            JSON Format: {{ "Pilihan Ganda": [{{ "tp": "..", "indikator": "..", "level": "L1", "soal": "..", "opsi": ["A. x", "B. y"], "kunci": "A", "skor": 2 }}], ... }}
            """
            
            with st.spinner("AI sedang bekerja..."):
                res = model.generate_content(prompt)
                data = json.loads(re.sub(r'```json|```', '', res.text).strip())
                st.session_state.preview_data = data
                
                # Info
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': 'IX', 'jenis_asesmen': jenis}
                
                d1, d_kunci, d_kisi = generate_docs_final(data, info_s, info_u)
                
                def b(d): 
                    io = BytesIO(); d.save(io); return io.getvalue()
                
                st.session_state.files = {'n': b(d1), 'k': b(d_kunci), 's': b(d_kisi)}
                st.success("Berhasil! Silakan unduh dokumen di bawah.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. PREVIEW & DOWNLOAD ---
if st.session_state.files:
    st.divider()
    # Tombol Download
    col1, col2, col3 = st.columns(3)
    col1.download_button("📥 Cetak Naskah Soal", st.session_state.files['n'], "Naskah_Soal.docx", "primary")
    col2.download_button("📥 Cetak Kunci & Pedoman", st.session_state.files['k'], "Kunci_Jawaban.docx", "primary")
    col3.download_button("📥 Cetak Kisi-Kisi", st.session_state.files['s'], "Kisi_Kisi.docx")

    st.divider()
    # Analisis Level Kognitif
    st.subheader("📊 Analisis Soal")
    df_preview = []
    for tipe, qs in st.session_state.preview_data.items():
        for q in qs:
            df_preview.append({"Bentuk": tipe, "Level": q.get('level', 'L2'), "Skor": q.get('skor', 0)})
    
    if df_preview:
        df = pd.DataFrame(df_preview)
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Sebaran Level Kognitif**")
            st.bar_chart(df['Level'].value_counts())
        with c2:
            st.write("**Rekapitulasi Skor**")
            st.metric("Total Skor", f"{df['Skor'].sum()} / 100")
            st.dataframe(df.groupby('Bentuk')['Skor'].sum())
