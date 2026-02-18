import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="AI Generator Asesmen Sumatif",
    page_icon="📝",
    layout="wide"
)

# --- 2. FUNGSI MEMBUAT FILE WORD ---
def create_docx(text):
    doc = Document()
    doc.add_heading('DOKUMEN ASESMEN SUMATIF', 0)
    
    # Menambahkan teks hasil AI ke dalam paragraf Word
    for line in text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
        else:
            doc.add_paragraph("") # Spasi antar paragraf
            
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. ANTARMUKA PENGGUNA (UI) ---
st.title("📝 AI Generator Perangkat Asesmen")
st.write("Aplikasi ini secara otomatis membuat Kisi-kisi, Soal, Kartu Soal, dan Pedoman Penskoran.")

with st.sidebar:
    st.header("Konfigurasi")
    api_key = st.text_input("Masukkan Gemini API Key:", type="password")
    st.info("Dapatkan API Key di: https://aistudio.google.com/app/apikey")
    st.markdown("---")
    st.write("Dibuat untuk membantu administrasi Guru.")

# Input Materi
materi = st.text_area("Tempelkan Materi Ajar di sini (Teks):", height=300, placeholder="Contoh: Materi tentang Ekosistem, Rantai Makanan, dsb...")

# --- 4. LOGIKA PROSES AI ---
if st.button("Generate Perangkat Asesmen"):
    if not api_key:
        st.error("❌ Silakan masukkan API Key di sidebar!")
    elif not materi:
        st.warning("⚠️ Silakan masukkan materi terlebih dahulu.")
    else:
        try:
            # Konfigurasi Google AI
            genai.configure(api_key=api_key)
            
            # Deteksi model yang tersedia secara otomatis
            with st.spinner("Mengecek ketersediaan model..."):
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Urutan prioritas model
                selected_model = None
                for target in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
                    if target in available_models:
                        selected_model = target
                        break
                
                if not selected_model:
                    selected_model = available_models[0]
                
                st.info(f"Menggunakan Model: **{selected_model}**")
                model = genai.GenerativeModel(selected_model)

            # Prompt Instruksi
            prompt = f"""
            Anda adalah pakar pembuat soal dan pengembang kurikulum. 
            Berdasarkan materi ajar berikut:
            ---
            {materi}
            ---
            
            Buatkan perangkat asesmen lengkap dalam bahasa Indonesia yang terdiri dari:
            1. TABEL KISI-KISI SOAL (No, Indikator Soal, Level Kognitif, Bentuk Soal, Nomor Soal).
            2. 5 BUTIR SOAL PILIHAN GANDA (Sertakan opsi A, B, C, D dan Kunci Jawaban).
            3. 1 CONTOH KARTU SOAL (Berisi detail indikator dan satu butir soal).
            4. PEDOMAN PENSKORAN (Cara menghitung nilai akhir siswa).
            
            Tampilkan dalam format Markdown yang rapi dengan tabel.
            """

            with st.spinner("AI sedang menyusun perangkat asesmen... Mohon tunggu."):
                response = model.generate_content(prompt)
                hasil_ai = response.text
                
                # Tampilkan Hasil di Layar
                st.success("✅ Berhasil Dibuat!")
                st.markdown("---")
                st.markdown(hasil_ai)
                st.markdown("---")
                
                # Fitur Download ke Word
                file_word = create_docx(hasil_ai)
                st.download_button(
                    label="📥 Download Hasil ke Microsoft Word (.docx)",
                    data=file_word,
                    file_name="perangkat_asesmen_sumatif.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis: {str(e)}")
            st.info("Saran: Periksa apakah API Key Anda benar atau kuota gratis telah habis.")

# --- 5. FOOTER ---
st.caption("Aplikasi AI Asesmen v1.0 | Streamlit & Gemini API")
