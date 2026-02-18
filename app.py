import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# Konfigurasi Halaman
st.set_page_config(page_title="Generator Asesmen AI", layout="centered")

def create_docx(text):
    doc = Document()
    doc.add_heading('Hasil Generasi Asesmen Sumatif', 0)
    # Memisahkan teks berdasarkan baris agar lebih rapi di Word
    for line in text.split('\n'):
        doc.add_paragraph(line)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

st.title("📝 AI Generator Soal & Kisi-kisi")
st.write("Buat administrasi soal lengkap hanya dengan upload/tempel materi.")

# Input di Sidebar
with st.sidebar:
    api_key = st.text_input("Masukkan Gemini API Key:", type="password")
    st.info("Dapatkan API Key di: https://aistudio.google.com/app/apikey")

# Input Materi
materi = st.text_area("Tempelkan materi ajar (Teks) di sini:", height=250)

# Tombol Eksekusi
if st.button("Proses Sekarang"):
    if not api_key:
        st.error("Silakan masukkan API Key di sidebar!")
    elif not materi:
        st.warning("Silakan tempelkan materi materi terlebih dahulu.")
    else:
        try:
            genai.configure(api_key=api_key)
            # Menggunakan model 1.5 Flash yang lebih baru & stabil
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Tolong buatkan perangkat asesmen lengkap berdasarkan materi berikut:
            {materi}
            
            Format yang diminta:
            1. Kisi-kisi Soal dalam bentuk tabel.
            2. 5 Soal Pilihan Ganda (A, B, C, D) dan Kunci Jawaban.
            3. 1 Contoh Kartu Soal.
            4. Pedoman Penskoran.
            """
            
            with st.spinner("AI sedang berpikir..."):
                response = model.generate_content(prompt)
                hasil_teks = response.text
                
                st.success("Berhasil dibuat!")
                st.markdown("---")
                st.markdown(hasil_teks)
                
                # Sediakan tombol download
                file_word = create_docx(hasil_teks)
                st.download_button(
                    label="📄 Download Sebagai file Word",
                    data=file_word,
                    file_name="perangkat_asesmen.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        except Exception as e:
            st.error(f"Gagal memproses. Detail error: {e}")
