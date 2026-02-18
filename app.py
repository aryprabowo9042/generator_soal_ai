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

# --- FUNGSI DOKUMEN (Sama seperti sebelumnya) ---
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
    c1 = table.cell(0, 0).paragraphs[0]; r1 = c1.add_run(f"MATA PELAJARAN : {info_ujian['mapel']}"); set_font(r1, 10)
    c2 = table.cell(0, 1).paragraphs[0]; r2 = c2.add_run(f"WAKTU : {info_ujian['waktu']} menit"); set_font(r2, 10)
    c3 = table.cell(1, 0).paragraphs[0]; r3 = c3.add_run("HARI/ TANGGAL : ..........................."); set_font(r3, 10)
    c4 = table.cell(1, 1).paragraphs[0]; r4 = c4.add_run(f"KELAS : {info_ujian['kelas']}"); set_font(r4, 10)
    doc.add_paragraph()

# --- FUNGSI GENERATE WORD ---
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
    idx = 0; no = 1
    for tipe, questions in data_soal.items():
        if not questions: continue
        p = doc.add_paragraph(); run = p.add_run(f"\n{abjad[idx]}. {headers.get(tipe, tipe)}"); set_font(run, bold=True)
        if tipe == "Benar Salah":
            tbl = doc.add_table(rows=1, cols=4); tbl.style = 'Table Grid'
            h = tbl.rows[0].cells; h[0].text='No'; h[1].text='Pernyataan'; h[2].text='B'; h[3].text='S'
            for q in questions:
                row = tbl.add_row().cells; row[0].text=f"{no}."; row[1].text=q['soal']; no+=1
            doc.add_paragraph()
        else:
            for q in questions:
                doc.add_paragraph(f"{no}. {q['soal']}")
                if 'opsi' in q and isinstance(q['opsi'], list):
                    p_opsi = doc.add_paragraph(); p_opsi.paragraph_format.left_indent = Inches(0.3)
                    lbls = ['A', 'B', 'C', 'D']; 
                    for i, o in enumerate(q['opsi']): 
                        if i<4: p_opsi.add_run(f"{lbls[i]}. {o}    ")
                no += 1
        idx += 1
    return doc

def generate_kartu_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"KARTU SOAL {info_ujian['jenis_asesmen'].upper()}\n{info_sekolah.get('nama_sekolah')}\nTAHUN 2025/2026"); set_font(run, bold=True)
    doc.add_paragraph(f"Guru: {info_ujian['guru']} | Mapel: {info_ujian['mapel']}")
    no = 1
    for tipe, questions in data_soal.items():
        if not questions: continue
        doc.add_paragraph(f"\nBentuk: {tipe}")
        for q in questions:
            doc.add_paragraph(f"Soal No: {no}")
            tbl = doc.add_table(rows=6, cols=2); tbl.style = 'Table Grid'
            tbl.columns[0].width = Inches(1.5); tbl.columns[1].width = Inches(5.0)
            kunci = q.get('kunci', '-') if tipe != 'Uraian' else q.get('skor', '-')
            dt = [("No", str(no)), ("TP", q.get('tp','-')), ("Indikator", q.get('indikator','-')), ("Level", q.get('level','-')), ("Soal", q['soal']), ("Kunci/Skor", kunci)]
            for i, (l, v) in enumerate(dt): tbl.cell(i,0).text=l; tbl.cell(i,1).text=str(v)
            doc.add_paragraph(); no += 1
    return doc

def generate_kisi_kisi(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"KISI-KISI {info_ujian['jenis_asesmen'].upper()}\n{info_sekolah.get('nama_sekolah')}\nTAHUN 2025/2026"); set_font(run, bold=True)
    doc.add_paragraph(f"Guru: {info_ujian['guru']} | Mapel: {info_ujian['mapel']}")
    tbl = doc.add_table(rows=1, cols=6); tbl.style = 'Table Grid'
    for i, h in enumerate(["No", "TP", "Indikator", "Level", "Bentuk", "No Soal"]): tbl.cell(0, i).text = h
    no = 1
    for tipe, questions in data_soal.items():
        for q in questions:
            r = tbl.add_row().cells
            r[0].text=str(no); r[1].text=q.get('tp','-'); r[2].text=q.get('indikator','-'); r[3].text=q.get('level','-'); r[4].text=tipe; r[5].text=str(no)
            no += 1
    return doc

# --- UI STREAMLIT ---
st.title("📝 Generator Soal SMP Muhammadiyah (Versi Stabil)")
st.info("Pastikan requirements.txt berisi: google-generativeai>=0.7.2")

with st.sidebar:
    api_key = st.text_input("Gemini API Key (Wajib)", type="password")
    st.markdown("[Klik disini untuk buat Key Baru](https://aistudio.google.com/app/apikey)")
    st.markdown("---")
    sekolah = st.text_input("Sekolah", value="SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", value="................")
    nbm = st.text_input("NBM", value=".......")

c1, c2 = st.columns(2)
with c1:
    mapel = st.text_input("Mata Pelajaran")
    kelas = st.text_input("Kelas", value="VII / Genap")
with c2:
    waktu = st.number_input("Waktu (menit)", value=90)
    jenis = st.selectbox("Jenis Asesmen", ["Sumatif Lingkup Materi", "Asesmen Tengah Semester (ATS)", "Asesmen Akhir Semester (AAS)"])

st.subheader("Konfigurasi Soal")
opts = ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar Salah", "Isian Singkat", "Uraian"]
sel = st.multiselect("Bentuk Soal:", opts, default=["Pilihan Ganda", "Uraian"])
conf = {}
for x in sel: conf[x] = st.number_input(f"Jml {x}", 1, 10, 5)

materi = st.text_area("Tempelkan Materi / TP disini:", height=150)

if st.button("🚀 PROSES SEKARANG"):
    if not api_key or not materi:
        st.error("❌ API Key dan Materi tidak boleh kosong!")
    else:
        try:
            # 1. Konfigurasi
            genai.configure(api_key=api_key)
            
            # 2. Inisialisasi Model (Langsung ke 1.5 Flash)
            # Model ini paling stabil & gratis. Jika ini gagal, berarti Key salah.
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 3. Prompt JSON
            prompt = f"""
            Buatkan soal JSON dari materi: {materi}
            Format JSON Wajib:
            {{
                "Pilihan Ganda": [ {{ "tp": "-", "indikator": "-", "level": "L1", "soal": "-", "opsi": ["A", "B", "C", "D"], "kunci": "-" }} ],
                "Uraian": [ {{ "tp": "-", "indikator": "-", "level": "L3", "soal": "-", "skor": "-" }} ],
                "Benar Salah": [ {{ "tp": "-", "indikator": "-", "level": "L1", "soal": "Pernyataan", "kunci": "Benar/Salah" }} ],
                "Isian Singkat": [ {{ "tp": "-", "indikator": "-", "level": "L1", "soal": "-", "kunci": "-" }} ],
                "Pilihan Ganda Kompleks": [ {{ "tp": "-", "indikator": "-", "level": "L2", "soal": "-", "opsi": ["A", "B", "C", "D"], "kunci": "A dan C" }} ]
            }}
            Isi sesuai jumlah ini: {json.dumps(conf)}
            HANYA JSON. NO TEXT.
            """
            
            with st.spinner("Menghubungi Google AI..."):
                response = model.generate_content(prompt)
                
            # 4. Parsing
            try:
                txt = re.sub(r'```json|```', '', response.text).strip()
                data = json.loads(txt)
            except:
                st.error("AI memberikan respons tapi format JSON rusak. Coba materi lebih pendek.")
                st.stop()
                
            # 5. Generate Word
            info_s = {'nama_sekolah': sekolah, 'cabang': 'WELERI', 'tahun': '2025/2026'}
            info_u = {'mapel': mapel, 'kelas': kelas, 'waktu': waktu, 'jenis_asesmen': jenis, 'guru': guru, 'nbm': nbm}
            
            d1 = generate_naskah_soal(data, info_s, info_u)
            d2 = generate_kartu_soal(data, info_s, info_u)
            d3 = generate_kisi_kisi(data, info_s, info_u)
            
            def save(d): b = BytesIO(); d.save(b); return b.getvalue()
            
            st.success("✅ Berhasil! Silakan download:")
            ca, cb, cc = st.columns(3)
            ca.download_button("📥 1. Naskah Soal", save(d1), "1_Naskah.docx")
            cb.download_button("📥 2. Kartu Soal", save(d2), "2_Kartu.docx")
            cc.download_button("📥 3. Kisi-Kisi", save(d3), "3_Kisi.docx")
            
        except Exception as e:
            # MENAMPILKAN ERROR ASLI
            st.error(f"❌ GAGAL: {str(e)}")
            st.warning("Jika errornya '403/PermissionDenied': API Key Salah.")
            st.warning("Jika errornya '404/NotFound': Update file requirements.txt!")
