import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

st.set_page_config(page_title="Generator Asesmen", layout="wide")

st.title("📝 AI Generator Soal Sumatif")

with st.sidebar:
    api_key = st.text_input("Masukkan Gemini API Key:", type="password")
    st.info("Gunakan model: gemini-1.5-flash")

materi = st.text_area("Tempelkan materi ajar di sini:", height=300)

def create_docx(text):
    doc = Document()
    doc.add_heading('Paket Asesmen Sumatif', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

if st.button("Generate Paket Asesmen"):
    if not api_key:
        st.error("Masukkan API Key!")
    elif not materi:
        st.warning("Materi kosong.")
    else:
        try:
            genai.configure(api_key=api_key)
            # MENGGUNAKAN MODEL TERBARU
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"Buatkan kisi-kisi, soal pilihan ganda, kartu soal, dan pedoman skor dari materi ini: {materi}"
            
            with st.spinner("Sedang memproses..."):
                response = model.generate_content(prompt)
                hasil_ai = response.text
                
                st.markdown("### Hasil Generasi")
                st.markdown(hasil_ai)
                
                # Fitur Download
                docx_file = create_docx(hasil_ai)
                st.download_button(
                    label="📄 Download Hasil (Word)",
                    data=docx_file,
                    file_name="asesmen_sumatif.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
