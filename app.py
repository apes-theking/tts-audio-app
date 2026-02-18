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
    file.seek(0)
    image = Image.open(file)
    text = pytesseract.image_to_string(image)
    return [text]

def extract_text_from_pdf(file, force_ocr=False):
    """Extracts text from a PDF file, returning a list of strings (one per page)."""
    file.seek(0)
    pdf_bytes = file.read()
    pages = []

    if not force_ocr:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                pages.append(page.get_text())

    total_text_len = sum(len(p.strip()) for p in pages)

    # Fallback to OCR if forced, or if extracted text is empty/sparse
    if force_ocr or total_text_len < 50:
        images = convert_from_bytes(pdf_bytes)
        pages = []
        for image in images:
            pages.append(pytesseract.image_to_string(image))

    return pages

def extract_text_from_docx(file):
    """Extracts text from a DOCX file, returning a list of strings (chunked)."""
    file.seek(0)
    doc = docx.Document(file)
    pages = []
    current_chunk = ""
    for para in doc.paragraphs:
        para_text = para.text + "\n"
        if len(current_chunk) + len(para_text) > 1000 and current_chunk:
             pages.append(current_chunk)
             current_chunk = para_text
        else:
             current_chunk += para_text

    if current_chunk:
        pages.append(current_chunk)

    return pages

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

# Callbacks
def save_editor_content():
    """Saves the current editor content to the pages list."""
    if "pages" in st.session_state and "editor" in st.session_state:
        # Ensure we don't go out of bounds
        if 0 <= st.session_state.current_page < len(st.session_state.pages):
            st.session_state.pages[st.session_state.current_page] = st.session_state.editor

def prev_page():
    save_editor_content()
    if st.session_state.current_page > 0:
        st.session_state.current_page -= 1
        st.session_state.editor = st.session_state.pages[st.session_state.current_page]

def next_page():
    save_editor_content()
    if st.session_state.current_page < len(st.session_state.pages) - 1:
        st.session_state.current_page += 1
        st.session_state.editor = st.session_state.pages[st.session_state.current_page]

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

    # Initialize Session State
    if "pages" not in st.session_state:
        st.session_state.pages = []
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0
    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None
    if "last_force_ocr" not in st.session_state:
        st.session_state.last_force_ocr = False

    if uploaded_file is not None:
        # Check if file changed or OCR settings changed
        file_changed = (st.session_state.last_uploaded_file != uploaded_file.name)
        ocr_changed = (st.session_state.last_force_ocr != force_ocr)

        if file_changed or ocr_changed:
            file_type = uploaded_file.name.split(".")[-1].lower()

            with st.spinner("Extracting text..."):
                try:
                    if file_type == "pdf":
                        pages = extract_text_from_pdf(uploaded_file, force_ocr=force_ocr)
                    elif file_type == "docx":
                        pages = extract_text_from_docx(uploaded_file)
                    elif file_type in ["jpg", "jpeg", "png"]:
                        pages = extract_text_from_image(uploaded_file)
                    else:
                        st.error("Unsupported file format.")
                        return

                    cleaned_pages = [clean_text(page) for page in pages]
                    st.session_state.pages = cleaned_pages
                    st.session_state.current_page = 0
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.session_state.last_force_ocr = force_ocr

                    # Initialize editor content
                    if cleaned_pages:
                        st.session_state.editor = cleaned_pages[0]
                    else:
                        st.session_state.editor = ""

                except Exception as e:
                    st.error(f"Error extracting text: {e}")
                    return

        # UI Display
        if st.session_state.pages:
            # Pagination Controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.button("Previous Page", on_click=prev_page, disabled=(st.session_state.current_page == 0))
            with col2:
                st.markdown(f"<div style='text-align: center; line-height: 2.5em;'><b>Page {st.session_state.current_page + 1} of {len(st.session_state.pages)}</b></div>", unsafe_allow_html=True)
            with col3:
                st.button("Next Page", on_click=next_page, disabled=(st.session_state.current_page == len(st.session_state.pages) - 1))

            # Editor
            st.text_area("Edit Page Text", key="editor", height=300)

            # Audio Generation
            if st.button("Generate Audio for Whole Document"):
                save_editor_content() # Save current edits first
                full_text = "\n".join(st.session_state.pages)

                if not full_text.strip():
                    st.warning("No text found in the document.")
                else:
                    with st.spinner("Generating audio..."):
                        try:
                            audio_bytes = asyncio.run(generate_audio(full_text, selected_voice))

                            st.success("Audio generated successfully!")

                            st.audio(audio_bytes, format="audio/mp3")

                            st.download_button(
                                label="Download MP3",
                                data=audio_bytes,
                                file_name=f"{uploaded_file.name.split('.')[0]}.mp3",
                                mime="audio/mp3"
                            )
                        except Exception as e:
                            st.error(f"An error occurred during audio generation: {e}")
    else:
        # Reset state if file is removed
        if st.session_state.last_uploaded_file is not None:
            st.session_state.pages = []
            st.session_state.current_page = 0
            st.session_state.last_uploaded_file = None

if __name__ == "__main__":
    main()
