try:
            genai.configure(api_key=api_key)
            
            # Mencoba model flash terbaru
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                test_response = model.generate_content("test", generation_config={"max_output_tokens": 10})
            except:
                # Jika gagal, gunakan model pro sebagai cadangan
                model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"Buatkan kisi-kisi, soal pilihan ganda, kartu soal, dan pedoman skor dari materi ini: {materi}"
            
            with st.spinner("Sedang memproses..."):
                response = model.generate_content(prompt)
                
                if response.text:
                    st.markdown("### Hasil Generasi")
                    st.markdown(response.text)
                    
                    # Fitur Download
                    docx_file = create_docx(response.text)
                    st.download_button(
                        label="📄 Download Hasil (Word)",
                        data=docx_file,
                        file_name="asesmen_sumatif.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.error("AI tidak memberikan respon. Coba materi yang lebih pendek.")
                    
        except Exception as e:
            st.error(f"Kesalahan teknis: {str(e)}")
            st.info("Saran: Pastikan API Key Anda aktif dan dukung model Gemini 1.5.")
