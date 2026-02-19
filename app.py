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

# --- 2. DOKUMEN GENERATORS ---

def generate_docs_final(data_soal, info):
    # --- DOKUMEN 1: NASKAH SOAL ---
    d1 = Document()
    p = d1.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{t(info['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info['tahun_pelajaran'])}\n"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    # Tabel Identitas
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
            d1.add_paragraph(f"{no}. {q.get('soal')}")
            if "Pilihan Ganda" in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    d1.add_paragraph(f"    {['A','B','C','D'][i]}. {o}")
            no += 1

    # --- DOKUMEN 2: KUNCI & PEDOMAN ---
    d2 = Document()
    d2.add_heading(f"KUNCI JAWABAN & PEDOMAN PENSKORAN", 0)
    d2.add_paragraph(f"Mata Pelajaran: {info['mapel']}\nGuru: {info['guru']}")
    
    ktbl = d2.add_table(1, 4); ktbl.style = 'Table Grid'
    h = ktbl.rows[0].cells
    h[0].text="No"; h[1].text="Bentuk"; h[2].text="Kunci/Jawaban"; h[3].text="Skor"
    idx = 1
    for tipe, qs in data_soal.items():
        for q in qs:
            row = ktbl.add_row().cells
            row[0].text = str(idx); row[1].text = tipe
            row[2].text = str(q.get('kunci', q.get('pedoman', '-')))
            row[3].text = str(q.get('skor', 0))
            idx += 1
            
    return d1, d2

# --- 3. UI STREAMLIT ---
if 'preview_data' not in st.session_state: st.session_state.preview_data = None
if 'files' not in st.session_state: st.session_state.files = None

st.title("✅ Generator Soal SMP Muhammadiyah")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Nama Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")
    if st.button("🔄 Reset Aplikasi"):
        st.session_state.clear()
        st.rerun()

st.subheader("⚙️ Konfigurasi Asesmen")
jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester",
    "Asesmen Formatif Lingkup Materi"
])

bentuk_opsi = ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"]
pilihan_bentuk = st.multiselect("Pilih Bentuk Soal", bentuk_opsi, default=["Pilihan Ganda", "Uraian"])

conf = {b: st.number_input(f"Jumlah {b}", 1, 50, 5) for b in pilihan_bentuk}
materi = st.text_area("Masukkan Materi/Kisi-kisi", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("API Key dan Materi wajib diisi!")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # --- FIX: OTOMATIS CARI MODEL ---
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = 'models/gemini-1.5-flash'
            selected_model = target if target in models else models[0]
            
            model = genai.GenerativeModel(selected_model)
            
            prompt = f"""
            Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi}.
            Jumlah soal: {json.dumps(conf)}. TOTAL SKOR HARUS 100.
            
            Output JSON murni:
            {{
              "Pilihan Ganda": [{{ "soal": "..", "opsi": [".."], "kunci": "A", "skor": 2 }}],
              "Pilihan Ganda Kompleks": [{{ "soal": "..", "opsi": [".."], "kunci": "A,C", "skor": 4 }}],
              "Benar/Salah": [{{ "soal": "..", "kunci": "B", "skor": 2 }}],
              "Isian Singkat": [{{ "soal": "..", "kunci": "..", "skor": 5 }}],
              "Uraian": [{{ "soal": "..", "pedoman": "..", "skor": 15 }}]
            }}
            """
            
            with st.spinner(f"AI menggunakan {selected_model}..."):
                res = model.generate_content(prompt)
                clean_json = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(clean_json)
                st.session_state.preview_data = data
                
                info_data = {
                    'nama_sekolah': sekolah, 'guru': guru, 'mapel': mapel, 
                    'kelas': kelas, 'semester': semester, 'tahun_pelajaran': tahun,
                    'jenis_asesmen': jenis_asesmen
                }
                
                d1, d2 = generate_docs_final(data, info_data)
                
                def b(d): 
                    io = BytesIO(); d.save(io); return io.getvalue()
                
                st.session_state.files = {'n': b(d1), 'k': b(d2)}
                st.success("Generate Berhasil!")
        except Exception as e:
            st.error(f"Kesalahan: {e}")

# --- 4. PREVIEW & DOWNLOAD ---
if st.session_state.preview_data:
    st.divider()
    col1, col2 = st.columns(2)
    col1.download_button("📥 Cetak Naskah Soal", st.session_state.files['n'], f"Naskah_{mapel}.docx")
    col2.download_button("📥 Cetak Kunci & Pedoman", st.session_state.files['k'], f"Kunci_{mapel}.docx")

    st.subheader("👁️ Preview Soal")
    st.info(f"**{jenis_asesmen.upper()}** | {mapel} | Kelas {kelas} - {semester} | Guru: {guru}")
    
    for tipe, qs in st.session_state.preview_data.items():
        with st.expander(f"Bagian: {tipe} ({len(qs)} soal)"):
            for idx, q in enumerate(qs):
                st.write(f"**{idx+1}. {q['soal']}**")
                if "Pilihan Ganda" in tipe:
                    st.write(f"Opsi: {', '.join(q.get('opsi', []))}")
                st.write(f"👉 *Kunci/Pedoman: {q.get('kunci', q.get('pedoman'))}* | Skor: {q.get('skor')}")
