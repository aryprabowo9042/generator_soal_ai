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

# --- FUNGSI FORMATTING DOKUMEN (Sesuai Template) ---

def set_font(run, font_name='Times New Roman', size=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold

def create_header(doc, info_sekolah, judul_dokumen):
    # Membuat Kop Surat Sesuai Template
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
    # Identitas Ujian
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

# --- GENERATOR DOKUMEN ---

def generate_naskah_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    create_header(doc, info_sekolah, info_ujian['jenis_asesmen'].upper())
    create_identity_block(doc, info_ujian)
    
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
        
        p = doc.add_paragraph()
        run = p.add_run(f"\n{urutan_abjad[idx_section]}. {tipe_headers.get(tipe, tipe)}")
        set_font(run, bold=True)
        
        if tipe == "Benar Salah":
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = 'No'; hdr[1].text = 'Pernyataan'; hdr[2].text = 'Benar'; hdr[3].text = 'Salah'
            for q in questions:
                row = table.add_row().cells
                row[0].text = str(global_no) + "."
                row[1].text = q['soal']
                global_no += 1
            doc.add_paragraph()
        else:
            for q in questions:
                p_soal = doc.add_paragraph()
                r_num = p_soal.add_run(f"{global_no}. {q['soal']}")
                set_font(r_num)
                
                if tipe in ["Pilihan Ganda", "Pilihan Ganda Kompleks"] and 'opsi' in q:
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

def generate_kartu_soal(data_soal, info_sekolah, info_ujian):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"KARTU SOAL {info_ujian['jenis_asesmen'].upper()}\n{info_sekolah.get('nama_sekolah', 'SMP MUHAMMADIYAH 1 WELERI')}\nTAHUN AJARAN {info_sekolah.get('tahun', '2025/2026')}")
    set_font(r, bold=True)
    
    doc.add_paragraph(f"Nama\t\t: {info_ujian['guru']}")
    doc.add_paragraph(f"Mata Pelajaran\t: {info_ujian['mapel']}")
    doc.add_paragraph(f"Kelas\t\t: {info_ujian['kelas']}")
    
    global_no = 1
    for tipe, questions in data_soal.items():
        if not questions: continue
        doc.add_paragraph(f"\nBentuk So
