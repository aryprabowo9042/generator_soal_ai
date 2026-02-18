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

def set_font(run, size=12, bold=False, font_name='Times New Roman'):
    try:
        run.font.name = font_name
        run.font.size = Pt(int(size))
        run.bold = bold
    except:
        pass

# --- 2. GENERATOR DOKUMEN (SESUAI TEMPLATE UNGGAHAN) ---

def generate_docs_final(data_soal, info_sekolah, info_ujian):
    # --- DOKUMEN 1: NASKAH SOAL ---
    d1 = Document()
    p = d1.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
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
    
    headers = {
        "Pilihan Ganda": "A. Pilihan Ganda\nBerilah tanda silang (x) pada A, B, C atau D pada jawaban yang paling benar!", 
        "Benar Salah": "B. Benar / Salah\nTentukan apakah pernyataan tersebut Benar (B) atau Salah (S).",
        "Uraian": "C. Uraian\nJawablah pertanyaan-pertanyaan berikut ini dengan cermat dan lengkap!", 
    }
    
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        p = d1.add_paragraph()
        r = p.add_run(headers.get(tipe, tipe)); set_font(r, bold=True)
        
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

    # --- DOKUMEN 2: KARTU SOAL (Sesuai KARTU SOAL.docx) ---
    d2 = Document()
    p = d2.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL {t(info_ujian['jenis_asesmen']).upper()}\n{t(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d2.add_paragraph(f"Nama: {t(info_ujian['guru'])} | Mapel: {t(info_ujian['mapel'])} | Kelas: {t(info_ujian['kelas'])}")
    
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        for q in quests:
            kartu_tbl = d2.add_table(6, 2); kartu_tbl.style = 'Table Grid'
            kunci_label = "Kunci Jawaban" if tipe != 'Uraian' else "Pedoman Penskoran"
            kunci_val = q.get('kunci', '-') if tipe != 'Uraian' else q.get('skor', '-')
            
            rows = [
                ("Nomor Soal", t(no)),
                ("Kompetensi Dasar / TP", t(q.get('tp', '-'))),
                ("Indikator Soal", t(q.get('indikator', '-'))), 
                ("Level Kognitif", t(q.get('level', '-'))), 
                ("Butir Soal", t(q.get('soal', '-'))), 
                (kunci_label, t(kunci_val))
            ]
            for i, (lab, val) in enumerate(rows):
                kartu_tbl.cell(i, 0).text = lab
                kartu_tbl.cell(i, 1).text = val
            d2.add_paragraph(); no += 1

    # --- DOKUMEN 3: KISI-KISI (Sesuai KISI-KISI.docx) ---
    d3 = Document()
    p = d3.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KISI-KISI SOAL {t(info_ujian['jenis_asesmen']).upper()}\n{t(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    
    kisi_tbl = d3.add_table(1, 6); kisi_tbl.style = 'Table Grid'
    headers_kisi = ["No", "Kompetensi Dasar / TP", "Indikator Soal", "Level Kognitif (LOTS/HOTS)", "Bentuk Soal", "Nomor Soal"]
    for i, h in enumerate(headers_kisi): kisi_tbl.cell(0, i).text = h
    
    no = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            row = kisi_tbl.add_row().cells
            row[0].text = t(no)
            row[1].text = t(q.get('tp', '-'))
            row[2].text = t(q.get('indikator', '-'))
            row[3].text = t(q.get('level', '-'))
            row[4].text = t(tipe)
            row[5].text = t(no)
            no += 1
            
    return d1, d2, d3

# --- 3. UI STREAMLIT ---
st.title("✅ Generator Soal (Fix Model 404)")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # CEK MODEL YANG TERSEDIA
            models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = st.selectbox("Model Tersedia", models, index=0 if 'gemini-1.5-flash' in models else 0)
        except Exception:
            st.error("API Key tidak valid")
            target_model = "gemini-1.5-flash"
    else:
        target_model = "gemini-1.5-flash"

c1, c2 = st.columns(2)
sekolah = c1.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
guru = c1.text_input("Nama Guru", "................")
mapel = c2.text_input("Mata Pelajaran", "IPA")
kelas = c2.text_input("Kelas", "VII / Genap")
jenis = st.selectbox("Jenis Asesmen", ["Asesmen Tengah Semester (ATS)", "Asesmen Akhir Semester (AAS)", "Sumatif Lingkup Materi"])

opsi = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {k: st.number_input(f"Jumlah {k}", 1, 30, 5) for k in opsi}
materi = st.text_area("Masukkan Materi/Kisi-kisi (Paste di sini):", height=200)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("API Key & Materi wajib diisi!")
    else:
        try:
            model = genai.GenerativeModel(target_model)
            prompt = f"""
            Buat soal dalam format JSON murni. 
            Materi: {materi}
            Jumlah per tipe: {json.dumps(conf)}
            Format JSON:
            {{
                "Pilihan Ganda": [{{ "tp": "...", "indikator": "...", "level": "L1/L2/L3", "soal": "...", "opsi": ["A","B","C","D"], "kunci": "A" }}],
                "Benar Salah": [{{ "tp": "...", "indikator": "...", "level": "...", "soal": "...", "kunci": "B/S" }}],
                "Uraian": [{{ "tp": "...", "indikator": "...", "level": "...", "soal": "...", "skor": "Kunci/Pedoman" }}]
            }}
            Pastikan JSON valid dan HANYA output JSON.
            """
            
            with st.spinner(f"Menggunakan {target_model}..."):
                res = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(txt)
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': 90, 'jenis_asesmen': jenis, 'guru': guru}
                
                d1, d2, d3 = generate_docs_final(data, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                col1, col2, col3 = st.columns(3)
                col1.download_button("📥 Naskah", b(d1), "Naskah.docx")
                col2.download_button("📥 Kartu", b(d2), "Kartu.docx")
                col3.download_button("📥 Kisi-Kisi", b(d3), "Kisi.docx")
                st.success("Berhasil! Silakan unduh file.")
                
        except Exception as e:
            st.error(f"Error Detail: {str(e)}")
