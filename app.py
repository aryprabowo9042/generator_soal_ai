import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- KONFIGURASI ---
st.set_page_config(page_title="Generator Soal Final", layout="wide")

def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold

# --- PEMBUATAN DOKUMEN ---

def generate_docs_safe(data_soal, info_sekolah, info_ujian):
    # Kita bungkus semua akses data dengan str() langsung di tempat
    
    # 1. NASKAH SOAL
    d1 = Document()
    
    # Header
    p = d1.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 10, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {str(info_sekolah['cabang'])}\n"); set_font(r, 11, True)
    r = p.add_run(f"{str(info_sekolah['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{str(info_ujian['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {str(info_sekolah['tahun'])}"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    # Identitas
    t = d1.add_table(2, 2); t.autofit = True
    c = t.rows[0].cells
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {str(info_ujian['mapel'])}"); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"WAKTU : {str(info_ujian['waktu'])} menit"); set_font(r, 10)
    c = t.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"KELAS : {str(info_ujian['kelas'])}"); set_font(r, 10)
    d1.add_paragraph()
    
    # Isi Soal
    headers = {
        "Pilihan Ganda": "Pilihan Ganda\nSilanglah (x) jawaban yang benar!", 
        "Uraian": "Uraian\nJawablah dengan jelas!", 
        "Benar Salah": "Benar / Salah", 
        "Isian Singkat": "Isian Singkat",
        "Pilihan Ganda Kompleks": "Pilihan Ganda Kompleks"
    }
    abjad = ['A','B','C','D','E']
    idx = 0; no = 1
    
    for tipe, quests in data_soal.items():
        if not quests: continue
        
        # Judul Bagian
        p = d1.add_paragraph()
        judul = headers.get(tipe, tipe)
        r = p.add_run(f"\n{abjad[idx]}. {str(judul)}"); set_font(r, bold=True)
        
        if tipe == "Benar Salah":
            tbl = d1.add_table(1, 4); tbl.style = 'Table Grid'
            h = tbl.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests:
                row = tbl.add_row().cells
                row[0].text = str(no) + "." # PASTI STRING
                row[1].text = str(q.get('soal', '-')) # PASTI STRING
                no += 1
            d1.add_paragraph()
        else:
            for q in quests:
                soal_txt = str(q.get('soal', '-'))
                d1.add_paragraph(f"{str(no)}. {soal_txt}")
                
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p = d1.add_paragraph(); p.paragraph_format.left_indent = Inches(0.3)
                    lbl = ['A','B','C','D','E']
                    for i, o in enumerate(q['opsi']):
                        if i < 5:
                            p.add_run(f"{lbl[i]}. {str(o)}    ") # PASTI STRING
                no += 1
        idx += 1

    # 2. KARTU SOAL
    d2 = Document()
    p = d2.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL\n{str(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d2.add_paragraph(f"Mapel: {str(info_ujian['mapel'])} | Guru: {str(info_ujian['guru'])}")
    
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        d2.add_paragraph(f"\nBentuk: {str(tipe)}")
        for q in quests:
            d2.add_paragraph(f"Soal No: {str(no)}")
            tbl = d2.add_table(6, 2); tbl.style = 'Table Grid'
            tbl.columns[0].width = Inches(1.5); tbl.columns[1].width = Inches(5.0)
            
            kunci = q.get('kunci', '-') if tipe != 'Uraian' else q.get('skor', '-')
            
            # MEMAKSA SEMUA JADI STRING SATU PER SATU
            val_no = str(no)
            val_tp = str(q.get('tp', '-'))
            val_ind = str(q.get('indikator', '-'))
            val_lvl = str(q.get('level', '-'))
            val_soal = str(q.get('soal', '-'))
            val_kunci = str(kunci)
            
            # Masukkan ke tabel
            tbl.cell(0,0).text = "No";        tbl.cell(0,1).text = val_no
            tbl.cell(1,0).text = "TP";        tbl.cell(1,1).text = val_tp
            tbl.cell(2,0).text = "Indikator"; tbl.cell(2,1).text = val_ind
            tbl.cell(3,0).text = "Level";     tbl.cell(3,1).text = val_lvl
            tbl.cell(4,0).text = "Soal";      tbl.cell(4,1).text = val_soal
            tbl.cell(5,0).text = "Kunci";     tbl.cell(5,1).text = val_kunci
            
            d2.add_paragraph(); no += 1

    # 3. KISI-KISI
    d3 = Document()
    p = d3.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KISI-KISI SOAL\n{str(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d3.add_paragraph(f"Mapel: {str(info_ujian['mapel'])} | Kelas: {str(info_ujian['kelas'])}")
    
    tbl = d3.add_table(1, 6); tbl.style = 'Table Grid'
    cols = ["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]
    for i, h in enumerate(cols): tbl.cell(0, i).text = h
    
    no = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            r = tbl.add_row().cells
            r[0].text = str(no)
            r[1].text = str(q.get('tp', '-'))
            r[2].text = str(q.get('indikator', '-'))
            r[3].text = str(q.get('level', '-'))
            r[4].text = str(tipe)
            r[5].text = str(no)
            no += 1
            
    return d1, d2, d3

# --- UI STREAMLIT ---
st.title("✅ Generator Soal (Type-Safe Mode)")
st.caption("Versi ini memaksa semua data menjadi Text sebelum ditulis ke Word.")

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

opsi = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Uraian", "Benar Salah", "Isian Singkat"], default=["Pilihan Ganda", "Uraian"])
conf = {k: st.number_input(f"Jml {k}", 1, 20, 5, key=k) for k in opsi}
materi = st.text_area("Materi:", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("API Key & Materi wajib diisi!")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # Auto-Detect Model (Sama seperti sebelumnya)
            target = 'gemini-1.5-flash'
            try:
                ms = [m.name for m in genai.list_models()]
                for cand in ['models/gemini-2.5-flash', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash']:
                    if cand in ms: target = cand; break
            except: pass
            
            st.info(f"Model: {target}")
            model = genai.GenerativeModel(target)
            
            prompt = f"""
            Buat soal JSON dari materi: {materi}
            Format JSON Strict:
            {{
                "Pilihan Ganda": [{{ "tp": "-", "indikator": "-", "level": "L1", "soal": "-", "opsi": ["A","B","C","D"], "kunci": "-" }}],
                "Uraian": [{{ "tp": "-", "indikator": "-", "level": "L3", "soal": "-", "skor": "-" }}],
                "Benar Salah": [{{ "soal": "-", "kunci": "-", "tp": "-", "indikator": "-", "level": "-" }}],
                "Isian Singkat": [{{ "soal": "-", "kunci": "-", "tp": "-", "indikator": "-", "level": "-" }}]
            }}
            Jumlah: {json.dumps(conf)}
            HANYA JSON.
            """
            
            with st.spinner("AI sedang bekerja..."):
                res = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(txt)
                
                # Bungkus info sekolah/ujian agar aman
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
                
                d1, d2, d3 = generate_docs_safe(data, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                c1,c2,c3 = st.columns(3)
                c1.download_button("📥 Naskah", b(d1), "Naskah.docx")
                c2.download_button("📥 Kartu", b(d2), "Kartu.docx")
                c3.download_button("📥 Kisi-Kisi", b(d3), "Kisi.docx")
                
        except json.JSONDecodeError:
            st.warning("Gagal baca JSON. Coba lagi.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
