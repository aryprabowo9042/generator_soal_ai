import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Generator Asesmen", layout="wide")

st.title("📝 AI Generator Soal Sumatif")
st.subheader("Buat Kisi-kisi & Soal Otomatis")

# Sidebar untuk API Key
with st.sidebar:
    api_key = st.text_input("Masukkan Gemini API Key:", type="password")
    st.info("Dapatkan API Key di: https://aistudio.google.com/app/apikey")

# Input Materi
materi = st.text_area("Tempelkan materi ajar di sini:", height=300)

if st.button("Generate Paket Asesmen"):
    if not api_key:
        st.error("Silakan masukkan API Key terlebih dahulu!")
    elif not materi:
        st.warning("Materi tidak boleh kosong.")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Berdasarkan materi berikut: {materi}
        Buatkan:
        1. Kisi-kisi soal (Tabel: No, Kompetensi, Indikator Soal, Level Kognitif).
        2. 5 Soal Pilihan Ganda lengkap dengan kunci jawaban.
        3. Kartu Soal untuk salah satu soal tersebut.
        4. Pedoman Penskoran.
        Gunakan bahasa Indonesia yang formal.
        """
        
        with st.spinner("Sedang memproses..."):
            response = model.generate_content(prompt)
            st.markdown("---")
            st.markdown(response.text)
