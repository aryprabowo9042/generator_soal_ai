import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from io import BytesIO
import json
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

# --- FUNGSI UTAMA GENERATE DOKUMEN ---

def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold

def create_header(doc, info_sekolah, judul_dokumen):
    # Membuat Kop Surat Sederhana (Teks) sesuai template 
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
    
    doc.add_paragraph("__________________________________________________________________________")

def create_identity_block(doc, info_ujian):
    # Identitas sesuai template 
    table = doc.add_table(rows=2, cols=2)
    table.autofit = True
    
    # Baris 1
    c1 = table.cell(0, 0).paragraphs[0]
    r1 = c1.add_run(f"MATA PELAJARAN : {info_ujian['mapel']}")
    set_font(r1, size=10)
    
    c2 = table.cell(0, 1).paragraphs[0]
    r2 = c2.add_run(f"WAKTU : {info_ujian['waktu']} menit")
    set_font(r2, size=10)
    
    # Baris 2
    c3 = table.cell(1, 0).paragraphs[0]
    r3 = c3.add_run("HARI/ TANGGAL     : ...........................")
    set_font(r3, size=10)
    
    c4 = table.cell(1, 1).paragraphs[0]
    r4 = c4.add_run(f"KELAS : {info_ujian['kelas']}")
    set_font(r4, size=10)
    doc.add_paragraph()

# --- 1. DOKUMEN NASKAH SOAL ---
def generate_naskah_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    judul = info_ujian['jenis_asesmen'].upper()
    create_header(doc, info_sekolah, judul)
    create_identity_block(doc, info_ujian)
    
    # Mapping tipe soal ke Header Huruf (A, B, C...)
    tipe_headers = {
        "Pilihan Ganda": "Pilihan Ganda\nBerilah tanda silang (x) pada A, B, C atau D pada jawaban yang paling benar!",
        "Pilihan Ganda Kompleks": "Pilihan Ganda Kompleks\nPilihlah lebih dari satu jawaban yang benar!",
        "Benar Salah": "Benar / Salah\nTentukan apakah pernyataan tersebut Benar (B) atau Salah (S).",
        "Isian Singkat": "Isian Singkat\nIsilah titik-titik di bawah ini dengan jawaban yang tepat!",
        "Uraian": "Uraian\nJawablah pertanyaan-pertanyaan berikut ini dengan cermat dan lengkap!"
    }
    
    urutan_abjad = ['A', 'B', 'C', 'D', 'E']
    idx_section = 0
    global_no = 1
    
    for tipe, questions in data_soal.items():
        if not questions: continue
        
        # Header Section (Misal: A. Pilihan Ganda) [cite: 8-9]
        p = doc.add_paragraph()
        run = p.add_run(f"{urutan_abjad[idx_section]}. {tipe_headers.get(tipe, tipe)}")
        set_font(run, bold=True)
        
        # Tabel khusus untuk Benar/Salah [cite: 17]
        if tipe == "Benar Salah":
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'No'
            hdr_cells[1].text = 'Pernyataan'
            hdr_cells[2].text = 'Benar'
            hdr_cells[3].text = 'Salah'
            
            for q in questions:
                row_cells = table.add_row().cells
                row_cells[0].text = str(global_no) + "."
                row_cells[1].text = q['soal']
                global_no += 1
            doc.add_paragraph()
            
        else:
            # Loop Soal Biasa [cite: 10-14, 20-29]
            for q in questions:
                p_soal = doc.add_paragraph()
                r_num = p_soal.add_run(f"{global_no}. {q['soal']}")
                set_font(r_num)
                
                # Jika Pilihan Ganda, tampilkan opsi
                if tipe in ["Pilihan Ganda", "Pilihan Ganda Kompleks"]:
                    if 'opsi' in q and isinstance(q['opsi'], list):
                        # Format A. ... B. ... C. ... D. ...
                        p_opsi = doc.add_paragraph()
                        p_opsi.paragraph_format.left_indent = Inches(0.3)
                        labels = ['A', 'B', 'C', 'D', 'E']
                        for i, opt in enumerate(q['opsi']):
                            if i < len(labels):
                                r_opt = p_opsi.add_run(f"{labels[i]}. {opt}    ")
                                set_font(r_opt)
                
                global_no += 1
                
        idx_section += 1
        
    return doc

# --- 2. DOKUMEN KARTU SOAL ---
def generate_kartu_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p_judul = doc.add_paragraph()
    p_judul.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_judul.add_run(f"KARTU SOAL {info_ujian['jenis_asesmen'].upper()}\n{info_sekolah.get('nama_sekolah', 'SMP MUHAMMADIYAH 1 WELERI')}\nTAHUN AJARAN {info_sekolah.get('tahun', '2025/2026')}")
    set_font(r, bold=True)
    
    # Identitas [cite: 32-34]
    doc.add_paragraph(f"Nama\t\t: {info_ujian['guru']}")
    doc.add_paragraph(f"Mata Pelajaran\t: {info_ujian['mapel']}")
    doc.add_paragraph(f"Kelas\t\t: {info_ujian['kelas']}")
    
    global_no = 1
    urutan_abjad = ['A', 'B', 'C', 'D', 'E']
    idx_section = 0
    
    for tipe, questions in data_soal.items():
        if not questions: continue
        
        # Header Tipe [cite: 35]
        doc.add_paragraph(f"\n{urutan_abjad[idx_section]}. Bentuk Soal {tipe} ({len(questions)} Butir)")
        
        for q in questions:
            doc.add_paragraph(f"Soal Nomor {global_no}")
            
            # Tabel Kartu Soal 
            table = doc.add_table(rows=6, cols=2)
            table.style = 'Table Grid'
            table.autofit = False
            table.columns[0].width = Inches(2.0)
            table.columns[1].width = Inches(5.0)
            
            # Isi Tabel
            data_row = [
                ("Nomor Soal", str(global_no)),
                ("Kompetensi Dasar / TP", q.get('tp', '-')),
                ("Indikator Soal", q.get('indikator', '-')),
                ("Level Kognitif", q.get('level', '-')),
                ("Butir Soal", q['soal']),
                ("Kunci Jawaban / Pedoman Skor", q.get('kunci', '-') if tipe != "Uraian" else q.get('skor', '-'))
            ]
            
            for idx, (label, val) in enumerate(data_row):
                table.cell(idx, 0).text = label
                table.cell(idx, 1).text = str(val)
                
            doc.add_paragraph() # Spasi
            global_no += 1
            
        idx_section += 1
        
    # Tanda Tangan [cite: 78-81]
    doc.add_paragraph("\n")
    p_ttd = doc.add_paragraph(f"Weleri, .................................\nGuru Mapel\n\n\n({info_ujian['guru']})\nNBM. {info_ujian['nbm']}")
    
    return doc

# --- 3. DOKUMEN KISI-KISI ---
def generate_kisi_kisi(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p_judul = doc.add_paragraph()
    p_judul.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_judul.add_run(f"KISI-KISI SOAL {info_ujian['jenis_asesmen'].upper()}\n{info_sekolah.get('nama_sekolah', 'SMP MUHAMMADIYAH 1 WELERI')}\nTAHUN AJARAN {info_sekolah.get('tahun', '2025/2026')}")
    set_font(r, bold=True)
    
    # Identitas [cite: 84-86]
    doc.add_paragraph(f"Nama\t\t: {info_ujian['guru']}")
    doc.add_paragraph(f"Mata Pelajaran\t: {info_ujian['mapel']}")
    doc.add_paragraph(f"Kelas\t\t: {info_ujian['kelas']}")
    doc.add_paragraph()
    
    # Tabel Kisi-kisi 
    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'
    
    hdr = table.rows[0].cells
    headers = ["No", "Kompetensi Dasar / TP", "Indikator Soal", "Level Kognitif", "Bentuk Soal", "Nomor Soal"]
    for i, h in enumerate(headers):
        hdr[i].text = h
        set_font(hdr[i].paragraphs[0].runs[0], bold=True)
        
    global_no = 1
    for tipe, questions in data_soal.items():
        for q in questions:
            row = table.add_row().cells
            row[0].text = str(global_no)
            row[1].text = q.get('tp', '-')
            row[2].text = q.get('indikator', '-')
            row[3].text = q.get('level', '-')
            row[4].text = tipe
            row[5].text = str(global_no)
            global_no += 1

    # Tanda Tangan [cite: 89-92]
    doc.add_paragraph("\n")
    p_ttd = doc.add_paragraph(f"Weleri, .................................\nGuru Mapel\n\n\n({info_ujian['guru']})\nNBM. {info_ujian['nbm']}")
    
    return doc


# --- UI STREAMLIT ---

st.title("📝 Generator Perangkat Asesmen Lengkap")
st.markdown("Output: **Naskah Soal, Kisi-Kisi, dan Kartu Soal** sesuai format standar.")

# Sidebar Konfigurasi
with st.sidebar:
    st.header("1. Kredensial AI")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.header("2. Identitas Sekolah")
    nama_sekolah = st.text_input("Nama Sekolah", value="SMP MUHAMMADIYAH 1 WELERI")
    cabang = st.text_input("Cabang", value="WELERI")
    tahun_ajar = st.text_input("Tahun Ajaran", value="2025/2026")
    
    st.header("3. Identitas Guru")
    guru = st.text_input("Nama Guru", value="........................")
    nbm = st.text_input("NBM", value=".......")

# Input Data Utama
col1, col2 = st.columns(2)
with col1:
    mapel = st.text_input("Mata Pelajaran")
    kelas = st.text_input("Kelas/Semester", value="VII / Genap")
with col2:
    waktu = st.number_input("Alokasi Waktu (menit)", value=90, step=15)
    jenis_asesmen = st.selectbox("Pilih Jenis Asesmen", 
                                 ["Sumatif Lingkup Materi (1 TP)", 
                                  "Asesmen Tengah Semester (ATS)", 
                                  "Asesmen Akhir Semester (AAS)"])

st.divider()

# Konfigurasi Bentuk Soal (Dinamis)
st.subheader("Konfigurasi Bentuk Soal")
pilihan_bentuk = st.multiselect("Pilih bentuk soal yang ingin dibuat:", 
                                ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar Salah", "Isian Singkat", "Uraian"],
                                default=["Pilihan Ganda", "Uraian"])

config_soal = {}
for bentuk in pilihan_bentuk:
    jumlah = st.number_input(f"Jumlah Soal {bentuk}", min_value=1, value=5, key=bentuk)
    config_soal[bentuk] = jumlah

materi = st.text_area("Tempelkan Materi / Tujuan Pembelajaran (TP) di sini:", height=200)

# --- LOGIKA TOMBOL GENERATE ---
if st.button("🚀 PROSES DATA SEKARANG"):
    if not api_key or not materi or not config_soal:
        st.error("Mohon lengkapi API Key, Materi, dan Konfigurasi Soal.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prompt yang meminta output JSON murni
            prompt = f"""
            Anda adalah pakar pembuat soal. Buatkan soal berdasarkan materi berikut:
            {materi}
            
            Hasilkan output HANYA dalam format JSON. Jangan ada teks lain selain JSON.
            Struktur JSON harus seperti ini (keys harus persis sama):
            {{
                "Pilihan Ganda": [
                    {{
                        "tp": "Tujuan Pembelajaran singkat",
                        "indikator": "Indikator soal",
                        "level": "L1/L2/L3",
                        "soal": "Teks soal",
                        "opsi": ["Opsi A", "Opsi B", "Opsi C", "Opsi D"],
                        "kunci": "Kunci Jawaban (misal: A)"
                    }}
                ],
                "Uraian": [
                     {{
                        "tp": "Tujuan Pembelajaran singkat",
                        "indikator": "Indikator soal",
                        "level": "L3",
                        "soal": "Pertanyaan uraian",
                        "skor": "Pedoman penskoran detail"
                    }}
                ]
            }}
            
            Buatlah soal sesuai permintaan berikut:
            {json.dumps(config_soal)}
            
            Pastikan level kognitif bervariasi.
            """
            
            with st.spinner("AI sedang berpikir dan menyusun dokumen..."):
                response = model.generate_content(prompt)
                
                # Membersihkan output AI agar jadi JSON valid
                hasil_raw = response.text
                hasil_clean = re.sub(r'```json|```', '', hasil_raw).strip()
                data_soal = json.loads(hasil_clean)
                
                # Persiapan Data Info
                info_sekolah = {'nama_sekolah': nama_sekolah, 'cabang': cabang, 'tahun': tahun_ajar}
                info_ujian = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis_asesmen, 'guru': guru, 'nbm': nbm}
                
                # Generate Dokumen
                doc_naskah = generate_naskah_soal(data_soal, info_sekolah, info_ujian)
                doc_kartu = generate_kartu_soal(data_soal, info_sekolah, info_ujian)
                doc_kisi = generate_kisi_kisi(data_soal, info_sekolah, info_ujian)
                
                # Fungsi Helper Simpan
                def save_to_bio(doc):
                    bio = BytesIO()
                    doc.save(bio)
                    return bio.getvalue()
                
                # Tampilkan Tombol Download
                st.success("✅ Berhasil! Silakan unduh dokumen di bawah ini:")
                
                col_d1, col_d2, col_d3 = st.columns(3)
                
                with col_d1:
                    st.download_button(
                        label="📄 1. Naskah Soal (Word)",
                        data=save_to_bio(doc_naskah),
                        file_name="1_Naskah_Soal.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                with col_d2:
                    st.download_button(
                        label="📄 2. Kartu Soal (Word)",
                        data=save_to_bio(doc_kartu),
                        file_name="2_Kartu_Soal.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                    
                with col_d3:
                    st.download_button(
                        label="📄 3. Kisi-Kisi (Word)",
                        data=save_to_bio(doc_kisi),
                        file_name="3_Kisi_Kisi.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

        except Exception as e:
            st.error(f"Terjadi kesalahan: {str(e)}")
            st.warning("Coba ulangi proses. Jika error JSON parsing, AI mungkin menghasilkan format teks yang tidak standar.")
