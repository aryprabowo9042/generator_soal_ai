import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

# --- FUNGSI FORMATTING ---
def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold

def create_header(doc, info_sekolah, judul):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Gunakan str() untuk mencegah error jika data berupa angka
    r1 = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n")
    set_font(r1, 10, True)
    
    cabang = str(info_sekolah.get('cabang', 'WELERI'))
    r2 = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {cabang}\n")
    set_font(r2, 11, True)
    
    sekolah = str(info_sekolah.get('nama_sekolah', 'SMP MUHAMMADIYAH 1 WELERI'))
    r3 = p.add_run(f"{sekolah}\n")
    set_font(r3, 14, True)
    
    r4 = p.add_run(f"{str(judul)}\n")
    set_font(r4, 12, True)
    
    tahun = str(info_sekolah.get('tahun', '2025/2026'))
    r5 = p.add_run(f"TAHUN PELAJARAN {tahun}")
    set_font(r5, 11, True)
    
    doc.add_paragraph("_" * 75)

def create_identity(doc, info):
    t = doc.add_table(2, 2)
    t.autofit = True
    
    # Baris 1
    c = t.rows[0].cells
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {str(info['mapel'])}")
    set_font(r, 10)
    
    r = c[1].paragraphs[0].add_run(f"WAKTU : {str(info['waktu'])} menit")
    set_font(r, 10)
    
    # Baris 2
    c = t.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ...........................")
    set_font(r, 10)
    
    r = c[1].paragraphs[0].add_run(f"KELAS : {str(info['kelas'])}")
    set_font(r, 10)
    
    doc.add_paragraph()

# --- GENERATE DOKUMEN ---
def generate_docs(data_soal, info_sekolah, info_ujian):
    # 1. NASKAH SOAL
    d1 = Document()
    create_header(d1, info_sekolah, info_ujian['jenis_asesmen'].upper())
    create_identity(d1, info_ujian)
    
    headers = {
        "Pilihan Ganda": "Pilihan Ganda\nSilanglah (x) jawaban yang benar!", 
        "Uraian": "Uraian\nJawablah dengan jelas!", 
        "Benar Salah": "Benar / Salah\nTentukan Benar (B) atau Salah (S).", 
        "Isian Singkat": "Isian Singkat\nIsilah titik-titik dengan jawaban tepat!",
        "Pilihan Ganda Kompleks": "Pilihan Ganda Kompleks\nPilihlah lebih dari satu jawaban benar!"
    }
    
    abjad = ['A','B','C','D','E']
    idx = 0
    no = 1
    
    for tipe, quests in data_soal.items():
        if not quests: continue
        
        # Header Bagian (A, B, C...)
        p = d1.add_paragraph()
        label_tipe = headers.get(tipe, tipe)
        r = p.add_run(f"\n{abjad[idx]}. {label_tipe}")
        set_font(r, bold=True)
        
        if tipe == "Benar Salah":
            t = d1.add_table(1, 4)
            t.style = 'Table Grid'
            h = t.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            
            for q in quests:
                row = t.add_row().cells
                row[0].text = str(no) + "."
                row[1].text = str(q.get('soal', '-')) # FIX: Pakai str()
                no += 1
            d1.add_paragraph()
            
        else:
            for q in quests:
                soal_text = str(q.get('soal', '-')) # FIX: Pakai str()
                d1.add_paragraph(f"{no}. {soal_text}")
                
                # Opsi Jawaban
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p = d1.add_paragraph()
                    p.paragraph_format.left_indent = Inches(0.3)
                    opts = ['A','B','C','D','E']
                    for i, o in enumerate(q['opsi']): 
                        if i < 5: 
                            p.add_run(f"{opts[i]}. {str(o)}    ") # FIX: Pakai str()
                no += 1
        idx += 1

    # 2. KARTU SOAL
    d2 = Document()
    p = d2.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL\n{str(info_sekolah['nama_sekolah'])}")
    set_font(r, bold=True)
    d2.add_paragraph(f"Mapel: {str(info_ujian['mapel'])} | Guru: {str(info_ujian['guru'])}")
    
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        d2.add_paragraph(f"\nBentuk: {str(tipe)}")
        
        for q in quests:
            d2.add_paragraph(f"No: {no}")
            t = d2.add_table(6, 2)
            t.style = 'Table Grid'
            t.columns[0].width = Inches(1.5)
            t.columns[1].width = Inches(5.0)
            
            # Logika Kunci vs Skor
            isi_kunci = q.get('kunci', '-')
            if tipe == 'Uraian':
                isi_kunci = q.get('skor', '-')
            
            # Data Baris (Semua dibungkus str agar tidak error int)
            dt = [
                ("No", str(no)),
                ("TP", str(q.get('tp','-'))), 
                ("Indikator", str(q.get('indikator','-'))), 
                ("Level", str(q.get('level','-'))), 
                ("Soal", str(q.get('soal','-'))), 
                ("Kunci/Skor", str(isi_kunci))
            ]
            
            for i, (l, v) in enumerate(dt): 
                t.cell(i,0).text = l
                t.cell(i,1).text = v # v sudah pasti string karena di atas sudah di-str()
            
            d2.add_paragraph()
            no += 1

    # 3. KISI-KISI
    d3 = Document()
    p = d3.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KISI-KISI SOAL\n{str(info_sekolah['nama_sekolah'])}")
    set_font(r, bold=True)
    d3.add_paragraph(f"Mapel: {str(info_ujian['mapel'])} | Kelas: {str(info_ujian['kelas'])}")
    
    t = d3.add_table(1, 6)
    t.style = 'Table Grid'
    cols = ["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]
    for i, h in enumerate(cols): 
        t.cell(0, i).text = h
        
    no = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            r = t.add_row().cells
            r[0].text = str(no)
            r[1].text = str(q.get('tp','-'))
            r[2].text = str(q.get('indikator','-'))
            r[3].text = str(q.get('level','-'))
            r[4].text = str(tipe)
            r[5].text = str(no)
            no += 1

    return d1, d2, d3

# --- UI UTAMA ---
st.title("✅ Generator Soal SMP Muhammadiyah")
st.caption("Status: Connected to Gemini 2.5 Flash")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "................")
    nbm = st.text_input("NBM", ".......")

c1, c2 = st.columns(2)
mapel = c1.text_input("Mapel", "IPA")
kelas = c1.text_input("Kelas", "VII / Genap")
waktu = c2.number_input("Waktu (menit)", 90)
jenis = c2.selectbox("Jenis", ["Sumatif Lingkup Materi", "ATS", "AAS"])

opsi_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Uraian", "Benar Salah", "Isian Singkat", "Pilihan Ganda Kompleks"], default=["Pilihan Ganda", "Uraian"])

# Konfigurasi Jumlah
conf = {}
for k in opsi_soal:
    conf[k] = st.number_input(f"Jml {k}", min_value=1, value=5, key=k)

materi = st.text_area("Materi / TP:", height=150, placeholder="Contoh: Ekosistem dan Rantai Makanan...")

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("Lengkapi API Key dan Materi!")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # --- MODEL SELECTION ---
            # Kita prioritaskan model yang TERBUKTI berhasil di log Anda: 2.5 Flash
            target_model = 'gemini-2.5-flash'
            
            # Fallback jika user lain memakai kode ini
            try:
                models = [m.name for m in genai.list_models()]
                if 'models/gemini-2.5-flash' not in models:
                    target_model = 'gemini-1.5-flash' # Alternatif
            except:
                pass 
                
            model = genai.GenerativeModel(target_model)
            st.info(f"Memproses menggunakan: {target_model}")
            # -----------------------

            prompt = f"""
            Buatkan soal JSON (Strict) dari materi: {materi}
            
            Format JSON Wajib (Pastikan semua nilai adalah STRING, jangan integer):
            {{
                "Pilihan Ganda": [{{ "tp": "...", "indikator": "...", "level": "L1", "soal": "...", "opsi": ["A","B","C","D"], "kunci": "..." }}],
                "Uraian": [{{ "tp": "...", "indikator": "...", "level": "L3", "soal": "...", "skor": "..." }}],
                "Benar Salah": [{{ "soal": "...", "kunci": "Benar/Salah", "tp": "-", "indikator": "-", "level": "-" }}],
                "Isian Singkat": [{{ "soal": "...", "kunci": "...", "tp": "-", "indikator": "-", "level": "-" }}],
                "Pilihan Ganda Kompleks": [{{ "soal": "...", "opsi": ["A","B","C","D"], "kunci": "...", "tp": "-", "indikator": "-", "level": "-" }}]
            }}
            
            Jumlah soal: {json.dumps(conf)}
            PENTING: Hanya output JSON murni.
            """
            
            with st.spinner("AI sedang bekerja..."):
                response = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', response.text).strip()
                data_soal = json.loads(txt)
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
                
                d1, d2, d3 = generate_docs(data_soal, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                c1, c2, c3 = st.columns(3)
                c1.download_button("📥 Naskah Soal", b(d1), "1_Naskah.docx")
                c2.download_button("📥 Kartu Soal", b(d2), "2_Kartu.docx")
                c3.download_button("📥 Kisi-Kisi", b(d3), "3_Kisi.docx")

        except json.JSONDecodeError:
            st.error("Gagal membaca jawaban AI. Silakan tekan tombol PROSES sekali lagi.")
        except Exception as e:
            st.error(f"Terjadi kesalahan: {str(e)}")
            st.warning("Tips: Pastikan tidak ada karakter aneh di input materi.")
