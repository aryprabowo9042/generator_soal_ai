import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- 1. SETUP & FUNGSI PENGAMAN ---
st.set_page_config(page_title="Generator Soal Anti-Crash", layout="wide")

# Fungsi ini akan memaksa APAPUN menjadi String (Teks)
def aman(nilai):
    if nilai is None:
        return "-"
    return str(nilai).strip()

def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    try:
        run.font.size = Pt(int(size)) # Paksa size jadi integer untuk Pt
    except:
        run.font.size = Pt(12)
    run.bold = bold

# --- 2. GENERATOR DOKUMEN ---

def generate_docs_final(data_soal, info_sekolah, info_ujian):
    # DOKUMEN 1: NASKAH SOAL
    d1 = Document()
    
    # Header
    p = d1.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 10, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {aman(info_sekolah['cabang'])}\n"); set_font(r, 11, True)
    r = p.add_run(f"{aman(info_sekolah['nama_sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{aman(info_ujian['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {aman(info_sekolah['tahun'])}"); set_font(r, 11, True)
    d1.add_paragraph("_" * 75)
    
    # Identitas Ujian
    t = d1.add_table(2, 2); t.autofit = True
    c = t.rows[0].cells
    # Perhatikan penggunaan aman() di sini
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {aman(info_ujian['mapel'])}"); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"WAKTU : {aman(info_ujian['waktu'])} menit"); set_font(r, 10)
    c = t.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"KELAS : {aman(info_ujian['kelas'])}"); set_font(r, 10)
    d1.add_paragraph()
    
    # Loop Soal
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
        
        p = d1.add_paragraph()
        judul = headers.get(tipe, tipe)
        r = p.add_run(f"\n{abjad[idx]}. {aman(judul)}"); set_font(r, bold=True)
        
        if tipe == "Benar Salah":
            tbl = d1.add_table(1, 4); tbl.style = 'Table Grid'
            h = tbl.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests:
                row = tbl.add_row().cells
                # KUNCI UTAMA: aman(no) mengubah angka 1 jadi "1"
                row[0].text = aman(no) + "."
                row[1].text = aman(q.get('soal', '-'))
                no += 1
            d1.add_paragraph()
        else:
            for q in quests:
                soal_txt = aman(q.get('soal', '-'))
                d1.add_paragraph(f"{aman(no)}. {soal_txt}")
                
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p = d1.add_paragraph(); p.paragraph_format.left_indent = Inches(0.3)
                    lbl = ['A','B','C','D','E']
                    for i, o in enumerate(q['opsi']):
                        if i < 5:
                            p.add_run(f"{lbl[i]}. {aman(o)}    ") 
                no += 1
        idx += 1

    # DOKUMEN 2: KARTU SOAL
    d2 = Document()
    p = d2.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL\n{aman(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d2.add_paragraph(f"Mapel: {aman(info_ujian['mapel'])} | Guru: {aman(info_ujian['guru'])}")
    
    no = 1
    for tipe, quests in data_soal.items():
        if not quests: continue
        d2.add_paragraph(f"\nBentuk: {aman(tipe)}")
        for q in quests:
            d2.add_paragraph(f"Soal No: {aman(no)}")
            
            tbl = d2.add_table(6, 2); tbl.style = 'Table Grid'
            tbl.columns[0].width = Inches(1.5); tbl.columns[1].width = Inches(5.0)
            
            kunci = q.get('kunci', '-') if tipe != 'Uraian' else q.get('skor', '-')
            
            # Memasukkan data ke tabel dengan pembungkus aman()
            data_row = [
                ("No", aman(no)),
                ("TP", aman(q.get('tp', '-'))),
                ("Indikator", aman(q.get('indikator', '-'))),
                ("Level", aman(q.get('level', '-'))),
                ("Soal", aman(q.get('soal', '-'))),
                ("Kunci/Skor", aman(kunci))
            ]
            
            for i, (label, val) in enumerate(data_row):
                tbl.cell(i, 0).text = label
                tbl.cell(i, 1).text = val # val sudah pasti string karena aman()
            
            d2.add_paragraph(); no += 1

    # DOKUMEN 3: KISI-KISI
    d3 = Document()
    p = d3.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KISI-KISI SOAL\n{aman(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d3.add_paragraph(f"Mapel: {aman(info_ujian['mapel'])} | Kelas: {aman(info_ujian['kelas'])}")
    
    tbl = d3.add_table(1, 6); tbl.style = 'Table Grid'
    cols = ["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]
    for i, h in enumerate(cols): tbl.cell(0, i).text = h
    
    no = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            r = tbl.add_row().cells
            r[0].text = aman(no)
            r[1].text = aman(q.get('tp', '-'))
            r[2].text = aman(q.get('indikator', '-'))
            r[3].text = aman(q.get('level', '-'))
            r[4].text = aman(tipe)
            r[5].text = aman(no)
            no += 1
            
    return d1, d2, d3

# --- 3. UI STREAMLIT ---
st.title("✅ Generator Soal (Final Safe Mode)")
st.caption("Semua data angka dikonversi otomatis jadi teks.")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "................")
    nbm = st.text_input("NBM", ".......")

c1, c2 = st.columns(2)
mapel = c1.text_input("Mapel", "IPA")
kelas = c1.text_input("Kelas", "VII / Genap")
# Pastikan waktu diambil sebagai angka dulu, nanti di-convert
waktu_num = c2.number_input("Waktu (menit)", 90)
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
            
            # Auto Detect Model
            target = 'gemini-1.5-flash'
            try:
                ms = [m.name for m in genai.list_models()]
                for cand in ['models/gemini-2.5-flash', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash']:
                    if cand in ms: target = cand; break
            except: pass
            
            st.info(f"Menggunakan Model: {target}")
            model = genai.GenerativeModel(target)
            
            prompt = f"""
            Buat soal JSON dari: {materi}
            Format Strict JSON:
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
                
                # SANITASI DATA SEBELUM DIPROSES
                # Kita ubah semua angka jadi string disini agar aman
                info_s = {
                    'nama_sekolah': aman(sekolah),
                    'cabang': 'WELERI',
                    'tahun': '2025/2026'
                }
                info_u = {
                    'mapel': aman(mapel),
                    'kelas': aman(kelas),
                    'waktu': aman(waktu_num), # Convert angka 90 jadi string "90"
                    'jenis_asesmen': aman(jenis),
                    'guru': aman(guru),
                    'nbm': aman(nbm)
                }
                
                # Generate
                d1, d2, d3 = generate_docs_final(data, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                c1,c2,c3 = st.columns(3)
                c1.download_button("📥 Naskah", b(d1), "Naskah.docx")
                c2.download_button("📥 Kartu", b(d2), "Kartu.docx")
                c3.download_button("📥 Kisi-Kisi", b(d3), "Kisi.docx")
                
        except json.JSONDecodeError:
            st.warning("Gagal membaca JSON dari AI. Coba klik Proses lagi.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
