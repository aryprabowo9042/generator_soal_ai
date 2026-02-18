import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

# --- 2. FUNGSI FORMATTING DOKUMEN (Sesuai Template) ---

def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold

def create_header(doc, info_sekolah, judul_dokumen):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    r1 = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n")
    set_font(r1, size=10, bold=True)
    
    r2 = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {info_sekolah.get('cabang', 'WELERI')}\n")
    set_font(r2, size=11, bold=True)
    
    r3 = p.add_run(f"{info_sekolah.get('nama_sekolah', 'SMP MUHAMMADIYAH 1 WELERI')}\n")
    set_font(r3, size=14, bold=True)
    
    r4 = p.add_run(f"{judul_dokumen}\n")
    set_font(r4, size=12, bold=True)
    
    r5 = p.add_run(f"TAHUN PELAJARAN {info_sekolah.get('tahun', '2025/2026')}")
    set_font(r5, size=11, bold=True)
    
    doc.add_paragraph("_" * 75)

def create_identity(doc, info_ujian):
    table = doc.add_table(rows=2, cols=2)
    table.autofit = True
    
    c1 = table.cell(0, 0).paragraphs[0]
    r1 = c1.add_run(f"MATA PELAJARAN : {info_ujian['mapel']}")
    set_font(r1, size=10)
    
    c2 = table.cell(0, 1).paragraphs[0]
    r2 = c2.add_run(f"WAKTU : {info_ujian['waktu']} menit")
    set_font(r2, size=10)
    
    c3 = table.cell(1, 0).paragraphs[0]
    r3 = c3.add_run("HARI/ TANGGAL     : ...........................")
    set_font(r3, size=10)
    
    c4 = table.cell(1, 1).paragraphs[0]
    r4 = c4.add_run(f"KELAS : {info_ujian['kelas']}")
    set_font(r4, size=10)
    doc.add_paragraph()

# --- 3. FUNGSI GENERATE WORD ---

def generate_naskah_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    create_header(doc, info_sekolah, info_ujian['jenis_asesmen'].upper())
    create_identity(doc, info_ujian)
    
    headers = {
        "Pilihan Ganda": "Pilihan Ganda\nBerilah tanda silang (x) pada jawaban yang benar!",
        "Pilihan Ganda Kompleks": "Pilihan Ganda Kompleks\nPilihlah lebih dari satu jawaban benar!",
        "Benar Salah": "Benar / Salah\nTentukan Benar (B) atau Salah (S).",
        "Isian Singkat": "Isian Singkat\nIsilah titik-titik dengan jawaban tepat!",
        "Uraian": "Uraian\nJawablah dengan lengkap!"
    }
    
    abjad = ['A', 'B', 'C', 'D', 'E']
    idx = 0
    no = 1
    
    for tipe, questions in data_soal.items():
        if not questions: continue
        
        p = doc.add_paragraph()
        run = p.add_run(f"\n{abjad[idx]}. {headers.get(tipe, tipe)}")
        set_font(run, bold=True)
        
        if tipe == "Benar Salah":
            tbl = doc.add_table(rows=1, cols=4)
            tbl.style = 'Table Grid'
            hdr = tbl.rows[0].cells
            hdr[0].text = 'No'; hdr[1].text = 'Pernyataan'; hdr[2].text = 'B'; hdr[3].text = 'S'
            for q in questions:
                row = tbl.add_row().cells
                row[0].text = f"{no}."
                row[1].text = q['soal']
                no += 1
            doc.add_paragraph()
        else:
            for q in questions:
                p_soal = doc.add_paragraph()
                r_soal = p_soal.add_run(f"{no}. {q['soal']}")
                set_font(r_soal)
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p_opsi = doc.add_paragraph()
                    p_opsi.paragraph_format.left_indent = Inches(0.3)
                    labels = ['A', 'B', 'C', 'D', 'E']
                    for i, opt in enumerate(q['opsi']):
                        if i < len(labels):
                            r_opt = p_opsi.add_run(f"{labels[i]}. {opt}    ")
                            set_font(r_opt)
                no += 1
        idx += 1
    return doc

def generate_kartu_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    judul = f"KARTU SOAL {info_ujian['jenis_asesmen'].upper()}\n"
    judul += f"{info_sekolah.get('nama_sekolah', 'SMP MUH 1 WELERI')}\n"
    judul += f"TAHUN {info_sekolah.get('tahun', '2025/2026')}"
    r = p.add_run(judul)
    set_font(r, bold=True)
    
    doc.add_paragraph(f"Guru : {info_ujian['guru']}")
    doc.add_paragraph(f"Mapel : {info_ujian['mapel']}")
    
    no = 1
    for tipe, questions in data_soal.items():
        if not questions: continue
        doc.add_paragraph(f"\nBentuk: {tipe}")
        for q in questions:
            doc.add_paragraph(f"Soal No: {no}")
            tbl = doc.add_table(rows=6, cols=2)
            tbl.style = 'Table Grid'
            tbl.columns[0].width = Inches(1.5); tbl.columns[1].width = Inches(5.0)
            
            kunci = q.get('kunci', '-')
            if tipe == 'Uraian': kunci = q.get('skor', '-')
            
            data = [("No", str(no)), ("TP", q.get('tp','-')), ("Indikator", q.get('indikator','-')), ("Level", q.get('level','-')), ("Soal", q['soal']), ("Kunci/Skor", kunci)]
            for i, (l, v) in enumerate(data):
                tbl.cell(i, 0).text = l
                tbl.cell(i, 1).text = str(v)
            doc.add_paragraph()
            no += 1
            
    doc.add_paragraph(f"\n\nWeleri, ....................\nGuru Mapel\n\n\n({info_ujian['guru']})\nNBM. {info_ujian['nbm']}")
    return doc

def generate_kisi_kisi(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    judul = f"KISI-KISI {info_ujian['jenis_asesmen'].upper()}\n"
    judul += f"{info_sekolah.get('nama_sekolah', 'SMP MUH 1 WELERI')}\n"
    judul += f"TAHUN {info_sekolah.get('tahun', '2025/2026')}"
    r = p.add_run(judul)
    set_font(r, bold=True)
    
    doc.add_paragraph(f"Guru: {info_ujian['guru']} | Mapel: {info_ujian['mapel']}")
    doc.add_paragraph()
    
    tbl = doc.add_table(rows=1, cols=6)
    tbl.style = 'Table Grid'
    hdrs = ["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]
    for i, h in enumerate(hdrs): tbl.cell(0, i).text = h
        
    no = 1
    for tipe, questions in data_soal.items():
        for q in questions:
            row = tbl.add_row().cells
            row[0].text = str(no)
            row[1].text = q.get('tp', '-')
            row[2].text = q.get('indikator', '-')
            row[3].text = q.get('level', '-')
            row[4].text = tipe
            row[5].text = str(no)
            no += 1
            
    doc.add_paragraph(f"\n\nWeleri, ....................\nGuru Mapel\n\n\n({info_ujian['guru']})\nNBM. {info_ujian['nbm']}")
    return doc

# --- 4. UI STREAMLIT & LOGIKA UTAMA ---

st.title("📝 Generator Soal SMP Muhammadiyah")
st.caption("Solusi Fix 404 & Syntax Error")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown("---")
    sekolah = st.text_input("Sekolah", value="SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", value="................")
    nbm = st.text_input("NBM", value=".......")

c1, c2 = st.columns(2)
with c1:
    mapel = st.text_input("Mapel")
    kelas = st.text_input("Kelas", value="VII / Genap")
with c2:
    waktu = st.number_input("Waktu (menit)", value=90)
    jenis = st.selectbox("Jenis", ["Sumatif Lingkup Materi", "Asesmen Tengah Semester (ATS)", "Asesmen Akhir Semester (AAS)"])

st.subheader("Konfigurasi Soal")
opts = ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar Salah", "Isian Singkat", "Uraian"]
choices = st.multiselect("Bentuk Soal:", opts, default=["Pilihan Ganda", "Uraian"])
config = {}
for c in choices:
    config[c] = st.number_input(f"Jml {c}", min_value=1, value=5, key=c)

materi = st.text_area("Materi / Tujuan Pembelajaran:", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("API Key & Materi wajib diisi!")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # --- LOGIKA BARU: ACTIVE MODEL TESTING ---
            # Kita tidak lagi melihat list, tapi mencoba satu per satu sampai berhasil.
            # Urutan prioritas: Flash (Cepat/Gratis) -> Pro 1.5 -> Pro 1.0
            
            candidate_models = [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.0-pro",
                "gemini-pro"
            ]
            
            active_model = None
            
            with st.spinner("Sedang mencari koneksi model AI terbaik..."):
                for m_name in candidate_models:
                    try:
                        # Test 'ping' ke model
                        test_model = genai.GenerativeModel(m_name)
                        test_model.generate_content("Tes koneksi.")
                        active_model = m_name
                        break # Jika berhasil, stop loop
                    except Exception:
                        continue # Jika gagal, coba model berikutnya
            
            if not active_model:
                st.error("Gagal terhubung ke semua model Gemini. Pastikan API Key benar.")
                st.stop()
                
            st.success(f"Terhubung menggunakan model: {active_model}")
            model = genai.GenerativeModel(active_model)
            # -----------------------------------------
            
            prompt = f"""
            Buatkan soal dari materi ini: {materi}
            
            Hasilkan HANYA JSON valid. Jangan ada teks lain.
            Format JSON Wajib:
            {{
                "Pilihan Ganda": [
                    {{ "tp": "...", "indikator": "...", "level": "...", "soal": "...", "opsi": ["A", "B", "C", "D"], "kunci": "..." }}
                ],
                "Uraian": [
                    {{ "tp": "...", "indikator": "...", "level": "...", "soal": "...", "skor": "..." }}
                ],
                 "Benar Salah": [
                    {{ "tp": "...", "indikator": "...", "level": "...", "soal": "Pernyataan...", "kunci": "Benar/Salah" }}
                ]
            }}
            
            Sesuaikan jumlah soal dengan konfigurasi ini: {json.dumps(config)}
            """
            
            with st.spinner("AI sedang menyusun soal & dokumen..."):
                response = model.generate_content(prompt)
                
                # Bersihkan format Markdown JSON ```json ... ```
                text_clean = re.sub(r'```json|```', '', response.text).strip()
                
                # Parsing JSON
                try:
                    data_soal = json.loads(text_clean)
                except json.JSONDecodeError:
                    st.error("Gagal membaca format data dari AI. Silakan coba tekan tombol PROSES sekali lagi.")
                    st.stop()
                
                # Info Dokumen
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
                
                # Generate
                d1 = generate_naskah_soal(data_soal, info_s, info_u)
                d2 = generate_kartu_soal(data_soal, info_s, info_u)
                d3 = generate_kisi_kisi(data_soal, info_s, info_u)
                
                def get_bio(d):
                    b = BytesIO(); d.save(b); return b.getvalue()
                
                # Tombol Download
                col_a, col_b, col_c = st.columns(3)
                col_a.download_button("📥 1. Naskah Soal", get_bio(d1), "1_Naskah.docx")
                col_b.download_button("📥 2. Kartu Soal", get_bio(d2), "2_Kartu.docx")
                col_c.download_button("📥 3. Kisi-Kisi", get_bio(d3), "3_Kisi.docx")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis: {e}")
