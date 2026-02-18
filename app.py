import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import json
import re

# --- SETUP ---
st.set_page_config(page_title="Generator Soal Otomatis", layout="wide")

# --- FORMATTING DOKUMEN ---
def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name; run.font.size = Pt(size); run.bold = bold

def create_header(doc, info_sekolah, judul):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r1, 10, True)
    r2 = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH {info_sekolah.get('cabang', 'WELERI')}\n"); set_font(r2, 11, True)
    r3 = p.add_run(f"{info_sekolah.get('nama_sekolah', 'SMP MUHAMMADIYAH 1 WELERI')}\n"); set_font(r3, 14, True)
    r4 = p.add_run(f"{judul}\n"); set_font(r4, 12, True)
    r5 = p.add_run(f"TAHUN PELAJARAN {info_sekolah.get('tahun', '2025/2026')}"); set_font(r5, 11, True)
    doc.add_paragraph("_" * 75)

def create_identity(doc, info):
    t = doc.add_table(2, 2); t.autofit = True
    c = t.rows[0].cells; r=c[0].paragraphs[0].add_run(f"MATA PELAJARAN : {info['mapel']}"); set_font(r, 10)
    r=c[1].paragraphs[0].add_run(f"WAKTU : {info['waktu']} menit"); set_font(r, 10)
    c = t.rows[1].cells; r=c[0].paragraphs[0].add_run("HARI/ TANGGAL : ..........................."); set_font(r, 10)
    r=c[1].paragraphs[0].add_run(f"KELAS : {info['kelas']}"); set_font(r, 10)
    doc.add_paragraph()

# --- GENERATE DOCS ---
def generate_docs(data_soal, info_sekolah, info_ujian):
    # 1. NASKAH SOAL
    d1 = Document()
    create_header(d1, info_sekolah, info_ujian['jenis_asesmen'].upper())
    create_identity(d1, info_ujian)
    
    headers = {"Pilihan Ganda": "Pilihan Ganda\nSilanglah (x) jawaban yang benar!", "Uraian": "Uraian\nJawablah dengan jelas!", "Benar Salah": "Benar / Salah", "Isian Singkat": "Isian Singkat"}
    abjad = ['A','B','C','D','E']; idx=0; no=1
    
    for tipe, quests in data_soal.items():
        if not quests: continue
        p=d1.add_paragraph(); r=p.add_run(f"\n{abjad[idx]}. {headers.get(tipe, tipe)}"); set_font(r, bold=True)
        if tipe=="Benar Salah":
            t=d1.add_table(1,4); t.style='Table Grid'; h=t.rows[0].cells; h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in quests: r=t.add_row().cells; r[0].text=f"{no}."; r[1].text=q['soal']; no+=1
            d1.add_paragraph()
        else:
            for q in quests:
                d1.add_paragraph(f"{no}. {q['soal']}")
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p=d1.add_paragraph(); p.paragraph_format.left_indent=Inches(0.3)
                    opts=['A','B','C','D']; 
                    for i,o in enumerate(q['opsi']): 
                        if i<4: p.add_run(f"{opts[i]}. {o}    ")
                no+=1
        idx+=1

    # 2. KARTU SOAL
    d2 = Document()
    p=d2.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(f"KARTU SOAL\n{info_sekolah['nama_sekolah']}"); set_font(r, bold=True)
    d2.add_paragraph(f"Mapel: {info_ujian['mapel']} | Guru: {info_ujian['guru']}")
    no=1
    for tipe, quests in data_soal.items():
        if not quests: continue
        d2.add_paragraph(f"\nBentuk: {tipe}")
        for q in quests:
            d2.add_paragraph(f"No: {no}")
            t=d2.add_table(6,2); t.style='Table Grid'; t.columns[0].width=Inches(1.5); t.columns[1].width=Inches(5.0)
            kunci = q.get('kunci', '-') if tipe!='Uraian' else q.get('skor','-')
            dt=[("No", str(no)), ("TP", q.get('tp','-')), ("Indikator", q.get('indikator','-')), ("Level", q.get('level','-')), ("Soal", q['soal']), ("Kunci/Skor", kunci)]
            for i,(l,v) in enumerate(dt): t.cell(i,0).text=l; t.cell(i,1).text=str(v)
            d2.add_paragraph(); no+=1

    # 3. KISI-KISI
    d3 = Document()
    p=d3.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(f"KISI-KISI SOAL\n{info_sekolah['nama_sekolah']}"); set_font(r, bold=True)
    d3.add_paragraph(f"Mapel: {info_ujian['mapel']} | Kelas: {info_ujian['kelas']}")
    t=d3.add_table(1,6); t.style='Table Grid'; 
    for i,h in enumerate(["No","TP","Indikator","Level","Bentuk","No Soal"]): t.cell(0,i).text=h
    no=1
    for tipe, quests in data_soal.items():
        for q in quests:
            r=t.add_row().cells; r[0].text=str(no); r[1].text=q.get('tp','-'); r[2].text=q.get('indikator','-'); r[3].text=q.get('level','-'); r[4].text=tipe; r[5].text=str(no); no+=1

    return d1, d2, d3

# --- UI UTAMA ---
st.title("🛠️ Generator Soal Anti-Error 404")
st.caption("Versi Auto-Detect Model | Wajib Update requirements.txt ke google-generativeai==0.8.3")

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    if not api_key: st.warning("Masukkan API Key dulu!")
    st.divider()
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "................")
    nbm = st.text_input("NBM", ".......")

c1, c2 = st.columns(2)
mapel = c1.text_input("Mapel")
kelas = c1.text_input("Kelas", "VII / Genap")
waktu = c2.number_input("Waktu (menit)", 90)
jenis = c2.selectbox("Jenis", ["Sumatif Lingkup Materi", "ATS", "AAS"])

opsi_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Uraian", "Benar Salah", "Isian Singkat", "Pilihan Ganda Kompleks"], default=["Pilihan Ganda", "Uraian"])
conf = {k: st.number_input(f"Jml {k}", 1, 20, 5) for k in opsi_soal}
materi = st.text_area("Materi / TP:", height=150)

if st.button("🚀 PROSES"):
    if not api_key or not materi:
        st.error("Data belum lengkap!")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # --- LOGIKA PENCARI MODEL OTOMATIS (CORE FIX) ---
            active_model = None
            logs = []
            
            # 1. Cek apa yang tersedia di akun ini
            try:
                list_models = genai.list_models()
                available_names = [m.name for m in list_models if 'generateContent' in m.supported_generation_methods]
                logs.append(f"Model tersedia di akun: {available_names}")
                
                # 2. Prioritaskan model 1.5 Flash -> 1.5 Pro -> 1.0 Pro
                priorities = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
                
                for p in priorities:
                    if p in available_names:
                        active_model = p
                        break
                
                # 3. Jika tidak ada di prioritas, ambil sembarang yang pertama
                if not active_model and available_names:
                    active_model = available_names[0]
                    
            except Exception as e:
                logs.append(f"Gagal list_models: {e}")
            
            # 4. Final Fallback jika list_models gagal total
            if not active_model:
                active_model = 'gemini-pro' 
            
            st.success(f"✅ Menggunakan Model: {active_model}")
            # --------------------------------------------------

            model = genai.GenerativeModel(active_model)
            
            prompt = f"""
            Buatkan soal JSON (Strict) dari materi: {materi}
            Format: {{ "Pilihan Ganda": [{{ "tp": "-", "indikator": "-", "level": "L1", "soal": "-", "opsi": ["A","B","C","D"], "kunci": "-" }}], "Uraian": [{{ "tp": "-", "indikator": "-", "level": "L3", "soal": "-", "skor": "-" }}], "Benar Salah": [{{ "soal": "-", "kunci": "-" }}] }}
            Jumlah: {json.dumps(conf)}
            HANYA JSON.
            """
            
            with st.spinner("Sedang berpikir..."):
                res = model.generate_content(prompt)
                txt = re.sub(r'```json|```', '', res.text).strip()
                data = json.loads(txt)
                
                info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
                info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
                
                d1, d2, d3 = generate_docs(data, info_s, info_u)
                
                def b(d): bio=BytesIO(); d.save(bio); return bio.getvalue()
                
                c1, c2, c3 = st.columns(3)
                c1.download_button("📥 Naskah Soal", b(d1), "Naskah.docx")
                c2.download_button("📥 Kartu Soal", b(d2), "Kartu.docx")
                c3.download_button("📥 Kisi-Kisi", b(d3), "Kisi.docx")

        except Exception as e:
            st.error(f"❌ ERROR: {e}")
            st.code("\n".join(logs)) # Tampilkan log debug untuk diagnosa
            st.warning("Jika error JSONDecodeError: Klik PROSES lagi (AI kadang melamun).")
            st.warning("Jika error 404/Found: Lakukan LANGKAH 1 & 2 di panduan saya!")
