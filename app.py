import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- 1. SETUP ---
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

def clean_option(opt):
    """Menghapus prefix A. B. C. D. jika sudah ada dari AI agar tidak dobel"""
    return re.sub(r'^[A-D][.\s]+', '', str(opt)).strip()

# --- 2. GENERATOR DOKUMEN ---

def generate_docs_final(data_soal, info_sekolah, info_ujian):
    # --- DOKUMEN 1: NASKAH SOAL ---
    d1 = Document()
    p = d1.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Header sesuai template [cite: 1, 2, 3, 4, 5]
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {t(info_sekolah['cabang'])}\n"); set_font(r, 12, True)
    r = p.add_run(f"{t(info_sekolah['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info_ujian['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info_sekolah['tahun'])}"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    # Identitas [cite: 6, 7]
    tbl = d1.add_table(2, 2); tbl.autofit = True
    c = tbl.rows[0].cells
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {t(info_ujian['mapel'])}"); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"WAKTU : {t(info_ujian['waktu'])} menit"); set_font(r, 10)
    c = tbl.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"KELAS : {t(info_ujian['kelas'])}"); set_font(r, 10)
    d1.add_paragraph()
    
    no = 1
    # Urutan: PG -> Benar Salah -> Uraian [cite: 8, 15, 18]
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        quests = data_soal.get(tipe, [])
        if not quests: continue
        
        p = d1.add_paragraph()
        if tipe == "Pilihan Ganda":
            r = p.add_run("A. Pilihan Ganda\n"); set_font(r, bold=True)
            r = p.add_run("Berilah tanda silang (x) pada A, B, C atau D pada jawaban yang paling benar!"); set_font(r, 11) # [cite: 9]
        elif tipe == "Benar Salah":
            r = p.add_run("B. Benar / Salah\n"); set_font(r, bold=True)
            r = p.add_run("Tentukan apakah pernyataan tersebut Benar (B) atau Salah (S)."); set_font(r, 11) # [cite: 16]
        else:
            r = p.add_run("C. Uraian\n"); set_font(r, bold=True)
            r = p.add_run("Jawablah pertanyaan-pertanyaan berikut ini dengan cermat dan lengkap!"); set_font(r, 11) # [cite: 19]

        if tipe == "Benar Salah":
            # Tabel Benar Salah [cite: 17]
            sub_tbl = d1.add_table(1, 4); sub_tbl.style = 'Table Grid'
            h = sub_tbl.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests:
                row = sub_tbl.add_row().cells
                row[0].text = t(no); row[1].text = t(q.get('soal', '-'))
                no += 1
        elif tipe == "Pilihan Ganda":
            for q in quests:
                d1.add_paragraph(f"{t(no)}. {t(q.get('soal', '-'))}")
                if 'opsi' in q and isinstance(q['opsi'], list):
                    # Opsi mendatar menggunakan tabel borderless agar rapi
                    opt_tbl = d1.add_table(1, 4)
                    opt_cells = opt_tbl.rows[0].cells
                    lbl = ['A','B','C','D']
                    for i, o in enumerate(q['opsi'][:4]):
                        clean_text = clean_option(o)
                        r = opt_cells[i].paragraphs[0].add_run(f"{lbl[i]}. {clean_text}")
                        set_font(r, 11)
                no += 1
        else: # Uraian
            for q in quests:
                d1.add_paragraph(f"{t(no)}. {t(q.get('soal', '-'))}")
                no += 1

    # --- DOKUMEN 2: KARTU SOAL [cite: 30, 37, 59] ---
    d2 = Document()
    p = d2.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL {t(info_ujian['jenis_asesmen']).upper()}\n{t(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    
    count = 1
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        quests = data_soal.get(tipe, [])
        for q in quests:
            kartu_tbl = d2.add_table(6, 2); kartu_tbl.style = 'Table Grid'
            kunci_label = "Kunci Jawaban" if tipe != 'Uraian' else "Pedoman Penskoran"
            kunci_val = q.get('kunci', '-') if tipe != 'Uraian' else q.get('skor', '-')
            
            rows = [
                ("Nomor Soal", t(count)),
                ("Kompetensi Dasar / TP", t(q.get('tp', '-'))),
                ("Indikator Soal", t(q.get('indikator', '-'))), 
                ("Level Kognitif", t(q.get('level', '-'))), 
                ("Butir Soal", t(q.get('soal', '-'))), 
                (kunci_label, t(kunci_val))
            ]
            for i, (lab, val) in enumerate(rows):
                kartu_tbl.cell(i, 0).text = lab
                kartu_tbl.cell(i, 1).text = val
            d2.add_paragraph(); count += 1

    # --- DOKUMEN 3: KISI-KISI [cite: 82, 88] ---
    d3 = Document()
    p = d3.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KISI-KISI SOAL {t(info_ujian['jenis_asesmen']).upper()}\n{t(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    
    kisi_tbl = d3.add_table(1, 6); kisi_tbl.style = 'Table Grid'
    headers_kisi = ["No", "Kompetensi Dasar / TP", "Indikator Soal", "Level Kognitif (LOTS/HOTS)", "Bentuk Soal", "Nomor Soal"]
    for i, h in enumerate(headers_kisi): kisi_tbl.cell(0, i).text = h
    
    count = 1
    for tipe in ["Pilihan Ganda", "Benar Salah", "Uraian"]:
        quests = data_soal.get(tipe, [])
        for q in quests:
            row = kisi_tbl.add_row().cells
            row[0].text = t(count)
            row[1].text = t(q.get('tp', '-'))
            row[2].text = t(q.get('indikator', '-'))
            row[3].text = t(q.get('level', '-'))
            row[4].text = t(tipe)
            row[5].text = t(count)
            count += 1
            
    return d1, d2, d3

# --- 3. UI STREAMLIT (DENGAN SESSION STATE) ---
if 'files_generated' not in st.session_state:
    st.session_state.files_generated = False
    st.session_state.d1_bytes = None
    st.session_state.d2_bytes = None
    st.session_state.d3_bytes = None

st.title("✅ Generator Soal (Final Version)")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    if st.button("Reset Aplikasi"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

c1, c2 = st.columns(2)
sekolah = c1.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
guru = c1.text_input("Nama Guru", "................")
mapel = c2.text_input("Mata Pelajaran", "Seni Budaya")
kelas = c2.text_input("Kelas", "VII / Genap")
jenis = st.selectbox("Jenis Asesmen", ["Asesmen Tengah Semester (ATS)", "Asesmen Akhir Semester (AAS)", "Sumatif"])

opsi = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar Salah", "Uraian"], default=["Pilihan Ganda", "Benar Salah", "Uraian"])
conf = {k: st.number_input(f"Jumlah {k}", 1, 30, 5) for k in opsi}
materi = st.text_area("Materi (Paste Kisi-kisi/Materi di sini):", height=200)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("Isi API Key & Materi dulu!")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Buat soal JSON dari materi: {materi}
            Jumlah: {json.dumps(conf)}
            Format JSON Strict (HANYA JSON):
            {{
                "Pilihan Ganda": [{{ "tp": "...", "indikator": "...", "level": "L1/L2/L3", "soal": "...", "opsi": ["Opsi A", "Opsi B", "Opsi C", "Opsi D"], "kunci": "A" }}],
                "Benar Salah": [{{ "tp": "...", "indikator": "...", "level": "...", "soal": "...", "kunci": "B" }}],
                "Uraian": [{{ "tp": "...", "indikator": "...", "level": "...", "soal": "...", "skor": "Kunci Jawaban" }}]
            }}
            """
            
            with st.spinner("AI sedang menyusun soal..."):
                res = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(txt)
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': 90, 'jenis_asesmen': jenis, 'guru': guru}
                
                d1, d2, d3 = generate_docs_final(data, info_s, info_u)
                
                def get_bytes(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                # Simpan di session state agar tidak reset
                st.session_state.d1_bytes = get_bytes(d1)
                st.session_state.d2_bytes = get_bytes(d2)
                st.session_state.d3_bytes = get_bytes(d3)
                st.session_state.files_generated = True
                
        except Exception as e:
            st.error(f"Gagal: {e}")

# Tampilkan tombol unduh jika file sudah siap
if st.session_state.files_generated:
    st.divider()
    st.subheader("📥 Unduh Dokumen")
    col1, col2, col3 = st.columns(3)
    col1.download_button("📥 Naskah Soal", st.session_state.d1_bytes, f"Naskah_{mapel}.docx")
    col2.download_button("📥 Kartu Soal", st.session_state.d2_bytes, f"Kartu_{mapel}.docx")
    col3.download_button("📥 Kisi-Kisi", st.session_state.d3_bytes, f"Kisi_{mapel}.docx")
    st.info("Aplikasi tidak akan reset sampai Anda menekan tombol 'Reset' atau memuat ulang halaman.")
