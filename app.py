import streamlit as st
import edge_tts
import asyncio
import io
import fitz  # pymupdf
import docx
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

def extract_text_from_image(file):
    """Extracts text from an image file."""
    image = Image.open(file)
    text = pytesseract.image_to_string(image)
    return text

def extract_text_from_pdf(file, force_ocr=False):
    """Extracts text from a PDF file."""
    file.seek(0)
    pdf_bytes = file.read()
    text = ""

    if not force_ocr:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()

    # Fallback to OCR if forced, or if extracted text is empty/sparse
    if force_ocr or not text.strip() or len(text.strip()) < 50:
        images = convert_from_bytes(pdf_bytes)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image)

    return text

def extract_text_from_docx(file):
    """Extracts text from a DOCX file."""
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def clean_text(text):
    """Cleans extracted text by removing excessive newlines and whitespace."""
    # Replace multiple newlines with a single newline
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return text

async def generate_audio(text, voice):
    """Generates audio from text using edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

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

    # OCR Settings
    force_ocr = st.sidebar.checkbox("Force OCR (for scanned docs)")

    # File Uploader
    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx", "jpg", "jpeg", "png"])

    if uploaded_file is not None:
        file_type = uploaded_file.name.split(".")[-1].lower()
        
        with st.spinner("Extracting text..."):
            if file_type == "pdf":
                text = extract_text_from_pdf(uploaded_file, force_ocr=force_ocr)
            elif file_type == "docx":
                text = extract_text_from_docx(uploaded_file)
            elif file_type in ["jpg", "jpeg", "png"]:
                text = extract_text_from_image(uploaded_file)
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
