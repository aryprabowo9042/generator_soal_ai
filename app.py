import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- 1. SETUP & HELPER ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

# Fungsi Penyelamat: Memaksa apapun jadi String agar tidak error
def s(value):
    if value is None: return "-"
    return str(value)

def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. FORMATTING HEADER ---
def create_header(doc, info_sekolah, judul):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Semua input dibungkus s()
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 10, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {s(info_sekolah.get('cabang', 'WELERI'))}\n"); set_font(r, 11, True)
    r = p.add_run(f"{s(info_sekolah.get('nama_sekolah', 'SMP MUH 1 WELERI'))}\n"); set_font(r, 14, True)
    r = p.add_run(f"{s(judul)}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {s(info_sekolah.get('tahun', '2025/2026'))}"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)

def create_identity(doc, info):
    t = doc.add_table(2, 2); t.autofit = True
    c = t.rows[0].cells
    r = c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {s(info['mapel'])}"); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"WAKTU : {s(info['waktu'])} menit"); set_font(r, 10)
    c = t.rows[1].cells
    r = c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r = c[1].paragraphs[0].add_run(f"KELAS : {s(info['kelas'])}"); set_font(r, 10)
    doc.add_paragraph()

# --- 3. GENERATOR ---
def generate_docs(data_soal, info_sekolah, info_ujian):
    # === A. NASKAH SOAL ===
    d1 = Document()
    create_header(d1, info_sekolah, s(info_ujian['jenis_asesmen']).upper())
    create_identity(d1, info_ujian)
    
    headers = {
        "Pilihan Ganda": "Pilihan Ganda\nSilanglah (x) jawaban yang benar!", 
        "Uraian": "Uraian\nJawablah dengan jelas!", 
        "Benar Salah": "Benar / Salah", 
        "Isian Singkat": "Isian Singkat",
        "Pilihan Ganda Kompleks": "Pilihan Ganda Kompleks"
    }
    abjad = ['A','B','C','D','E']; idx=0; no=1
    
    for tipe, quests in data_soal.items():
        if not quests: continue
        p=d1.add_paragraph(); r=p.add_run(f"\n{abjad[idx]}. {headers.get(tipe, tipe)}"); set_font(r, bold=True)
        
        if tipe=="Benar Salah":
            t=d1.add_table(1,4); t.style='Table Grid'; h=t.rows[0].cells
            h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests:
                r=t.add_row().cells
                r[0].text = s(no) + "."  # FIX: Pakai s()
                r[1].text = s(q.get('soal','-')) # FIX: Pakai s()
                no+=1
            d1.add_paragraph()
        else:
            for q in quests:
                # FIX: Pastikan soal jadi string
                d1.add_paragraph(f"{s(no)}. {s(q.get('soal','-'))}")
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p=d1.add_paragraph(); p.paragraph_format.left_indent=Inches(0.3)
                    lbl=['A','B','C','D','E']
                    for i,o in enumerate(q['opsi']): 
                        if i<5: p.add_run(f"{lbl[i]}. {s(o)}    ") # FIX: Pakai s()
                no+=1
        idx+=1

    # === B. KARTU SOAL ===
    d2 = Document()
    p=d2.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(f"KARTU SOAL\n{s(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d2.add_paragraph(f"Mapel: {s(info_ujian['mapel'])} | Guru: {s(info_ujian['guru'])}")
    
    no=1
    for tipe, quests in data_soal.items():
        if not quests: continue
        d2.add_paragraph(f"\nBentuk: {s(tipe)}")
        for q in quests:
            d2.add_paragraph(f"Soal No: {s(no)}")
            t=d2.add_table(6,2); t.style='Table Grid'; t.columns[0].width=Inches(1.5); t.columns[1].width=Inches(5.0)
            
            isi_kunci = q.get('kunci', '-') if tipe!='Uraian' else q.get('skor','-')
            
            # FIX TOTAL: Semua data dibungkus s()
            items = [
                ("No", s(no)), 
                ("TP", s(q.get('tp','-'))), 
                ("Indikator", s(q.get('indikator','-'))), 
                ("Level", s(q.get('level','-'))), 
                ("Soal", s(q.get('soal','-'))), 
                ("Kunci/Skor", s(isi_kunci))
            ]
            for i, (l, v) in enumerate(items):
                t.cell(i,0).text = l
                t.cell(i,1).text = v # v is guaranteed string
            d2.add_paragraph(); no+=1

    # === C. KISI-KISI ===
    d3 = Document()
    p=d3.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(f"KISI-KISI SOAL\n{s(info_sekolah['nama_sekolah'])}"); set_font(r, bold=True)
    d3.add_paragraph(f"Mapel: {s(info_ujian['mapel'])} | Kelas: {s(info_ujian['kelas'])}")
    
    t=d3.add_table(1,6); t.style='Table Grid'; 
    cols=["No","TP","Indikator","Level","Bentuk","No Soal"]
    for i,h in enumerate(cols): t.cell(0,i).text = h
        
    no=1
    for tipe, quests in data_soal.items():
        for q in quests:
            r=t.add_row().cells
            # FIX TOTAL: Bungkus s()
            r[0].text=s(no); r[1].text=s(q.get('tp','-')); r[2].text=s(q.get('indikator','-'))
            r[3].text=s(q.get('level','-')); r[4].text=s(tipe); r[5].text=s(no)
            no+=1
            
    return d1, d2, d3

# --- 4. UI STREAMLIT ---
st.title("✅ Generator Soal (Versi Final Anti-Error)")
st.caption("Auto-Detect Model + Type Safety Fix")

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

opsi = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Uraian", "Benar Salah", "Isian Singkat", "Pilihan Ganda Kompleks"], default=["Pilihan Ganda", "Uraian"])
conf = {k: st.number_input(f"Jml {k}", 1, 20, 5, key=k) for k in opsi}
materi = st.text_area("Materi:", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key or not materi:
        st.error("API Key & Materi wajib diisi!")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # AUTO DETECT MODEL
            model_target = 'gemini-1.5-flash' # Default aman
            try:
                ms = [m.name for m in genai.list_models()]
                # Cek prioritas model terbaru
                for cand in ['models/gemini-2.5-flash', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash']:
                    if cand in ms: model_target = cand; break
            except: pass
            
            st.success(f"Menggunakan Model: {model_target}")
            model = genai.GenerativeModel(model_target)
            
            prompt = f"""
            Buatkan soal JSON dari: {materi}
            Format Wajib JSON (Strict):
            {{
                "Pilihan Ganda": [{{ "tp": "-", "indikator": "-", "level": "L1", "soal": "-", "opsi": ["A","B","C","D"], "kunci": "-" }}],
                "Uraian": [{{ "tp": "-", "indikator": "-", "level": "L3", "soal": "-", "skor": "-" }}],
                "Benar Salah": [{{ "soal": "-", "kunci": "-", "tp": "-", "indikator": "-", "level": "-" }}],
                "Isian Singkat": [{{ "soal": "-", "kunci": "-", "tp": "-", "indikator": "-", "level": "-" }}],
                "Pilihan Ganda Kompleks": [{{ "soal": "-", "opsi": ["A","B"], "kunci": "-", "tp": "-", "indikator": "-", "level": "-" }}]
            }}
            Jumlah: {json.dumps(conf)}
            HANYA JSON MURNI.
            """
            
            with st.spinner("AI sedang bekerja..."):
                res = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(txt)
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
                
                d1, d2, d3 = generate_docs(data, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                c1,c2,c3 = st.columns(3)
                c1.download_button("📥 Naskah", b(d1), "Naskah.docx")
                c2.download_button("📥 Kartu", b(d2), "Kartu.docx")
                c3.download_button("📥 Kisi-Kisi", b(d3), "Kisi.docx")
                
        except json.JSONDecodeError:
            st.warning("AI gagal format JSON. Klik Proses lagi.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
