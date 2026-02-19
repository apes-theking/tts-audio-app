import streamlit as st
import edge_tts
import asyncio
import io
import fitz  # pymupdf
import docx

def extract_text_from_pdf(file):
    """Extracts text from a PDF file."""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        return "".join(page.get_text() for page in doc)

def extract_text_from_docx(file):
    """Extracts text from a DOCX file."""
    doc = docx.Document(file)
    return "".join(para.text + "\n" for para in doc.paragraphs)

def clean_text(text):
    """Cleans extracted text by removing excessive newlines and whitespace."""
    # Replace multiple newlines with a single newline
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return text

async def generate_audio(text, voice):
    """Generates audio from text using edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
    return b"".join(audio_chunks)

def main():
    st.title("Document to Speech Converter")
    st.markdown("Convert PDF and Word documents into natural-sounding speech using Microsoft Edge TTS.")

    # Sidebar for Voice Selection
    st.sidebar.header("Settings")
    voice_options = {
        "Australian Female": "en-AU-NatashaNeural",
        "Australian Male": "en-AU-WilliamNeural",
        "US Female": "en-US-AriaNeural",
        "US Male": "en-US-ChristopherNeural"
    }
    selected_voice_name = st.sidebar.selectbox("Select Voice", list(voice_options.keys()))
    selected_voice = voice_options[selected_voice_name]

    # File Uploader
    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx"])

    if uploaded_file is not None:
        file_type = uploaded_file.name.split(".")[-1].lower()
        
        with st.spinner("Extracting text..."):
            if file_type == "pdf":
                text = extract_text_from_pdf(uploaded_file)
            elif file_type == "docx":
                text = extract_text_from_docx(uploaded_file)
            else:
                st.error("Unsupported file format.")
                return

            cleaned_text = clean_text(text)
        
        st.subheader("Extracted Text Preview (First 500 chars)")
        st.text_area("Text Content", cleaned_text[:500] + "...", height=150)
        
        if st.button("Convert to Speech"):
            if not cleaned_text:
                st.warning("No text found in the document.")
            else:
                with st.spinner("Generating audio..."):
                    try:
                        audio_bytes = asyncio.run(generate_audio(cleaned_text, selected_voice))
                        
                        st.success("Audio generated successfully!")
                        
                        # Audio Player
                        st.audio(audio_bytes, format="audio/mp3")
                        
                        # Download Button
                        st.download_button(
                            label="Download MP3",
                            data=audio_bytes,
                            file_name=f"{uploaded_file.name.split('.')[0]}.mp3",
                            mime="audio/mp3"
                        )
                    except Exception as e:
                        st.error(f"An error occurred during audio generation: {e}")

if __name__ == "__main__":
    main()
