import streamlit as st
import edge_tts
import asyncio
import io
import fitz  # pymupdf
import docx
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import cv2
import numpy as np

def process_image_for_ocr(image, threshold_value=128):
    """
    Applies pre-processing to an image for better OCR results.
    Args:
        image: A PIL Image object.
        threshold_value: The manual threshold value for binary conversion.
    Returns:
        A processed image as a numpy array.
    """
    # Convert PIL Image to numpy array
    img_array = np.array(image)

    # Convert to grayscale
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    elif len(img_array.shape) == 3 and img_array.shape[2] == 4:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
    else:
        # Assuming already grayscale
        gray = img_array

    # Apply Binary Threshold
    _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

    return thresh

def extract_text_from_image(image):
    """Extracts text from a pre-processed image (numpy array or PIL Image)."""
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

    # File Uploader & Camera Input
    st.subheader("Input Source")
    input_method = st.radio("Choose input method:", ("Upload File", "Camera"))

    uploaded_file = None
    camera_file = None

    if input_method == "Upload File":
        uploaded_file = st.file_uploader("Upload a file", type=["pdf", "docx", "jpg", "jpeg", "png"])
    else:
        camera_file = st.camera_input("Take a photo")

    # Determine which file to use
    active_file = uploaded_file if input_method == "Upload File" else camera_file

    # Initialize Session State
    if "pages" not in st.session_state:
        st.session_state.pages = []
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0
    if "last_processed_file_id" not in st.session_state:
        st.session_state.last_processed_file_id = None
    if "last_force_ocr" not in st.session_state:
        st.session_state.last_force_ocr = False
    if "last_threshold_value" not in st.session_state:
        st.session_state.last_threshold_value = 128

    current_file_id = None
    if active_file is not None:
        # Simple ID: name + size
        current_file_id = f"{active_file.name}_{active_file.size}"

    # Threshold Slider (Only visible for images)
    threshold_val = 128
    is_image = False
    if active_file is not None:
         file_type = active_file.name.split(".")[-1].lower()
         if file_type in ["jpg", "jpeg", "png"]:
             is_image = True
             threshold_val = st.slider("Adjust Shadow/Contrast (Threshold)", 0, 255, 128, help="Slide until the text is clear black and the background is white.")

    if active_file is not None:
        # Check if file changed or OCR settings/Threshold changed
        file_changed = (st.session_state.last_processed_file_id != current_file_id)
        ocr_changed = (st.session_state.last_force_ocr != force_ocr)
        threshold_changed = (st.session_state.last_threshold_value != threshold_val)

        if file_changed or ocr_changed or (is_image and threshold_changed):
            file_type = active_file.name.split(".")[-1].lower()

            with st.spinner("Processing..."):
                try:
                    pages = []
                    processed_image = None
                    original_image = None

                    if file_type == "pdf":
                        pages = extract_text_from_pdf(active_file, force_ocr=force_ocr)
                    elif file_type == "docx":
                        pages = extract_text_from_docx(active_file)
                    elif file_type in ["jpg", "jpeg", "png"]:
                        # Rewind file just in case
                        active_file.seek(0)
                        original_image = Image.open(active_file)

                        # Process Image
                        processed_image = process_image_for_ocr(original_image, threshold_value=threshold_val)

                        # Store processed image in session state to display it
                        st.session_state.last_processed_image = processed_image
                        st.session_state.last_original_image = original_image

                        pages = extract_text_from_image(processed_image)
                    else:
                        st.error("Unsupported file format.")
                        return

                    cleaned_pages = [clean_text(page) for page in pages]
                    st.session_state.pages = cleaned_pages
                    st.session_state.current_page = 0
                    st.session_state.last_processed_file_id = current_file_id
                    st.session_state.last_force_ocr = force_ocr
                    st.session_state.last_threshold_value = threshold_val

                    # Initialize editor content
                    if cleaned_pages:
                        st.session_state.editor = cleaned_pages[0]
                    else:
                        st.session_state.editor = ""

                except Exception as e:
                    st.error(f"Error processing document: {e}")
                    return

        # Display Images if available (and relevant)
        if "last_processed_image" in st.session_state and is_image:
             with st.expander("👁️ View Processed Image", expanded=True):
                 col1, col2 = st.columns(2)
                 with col1:
                     if "last_original_image" in st.session_state:
                         st.image(st.session_state.last_original_image, caption="Original", use_container_width=True)
                 with col2:
                     st.image(st.session_state.last_processed_image, caption="What the AI Sees", use_container_width=True)

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
                                file_name=f"{active_file.name.split('.')[0]}.mp3",
                                mime="audio/mp3"
                            )
                        except Exception as e:
                            st.error(f"An error occurred during audio generation: {e}")
    else:
        # Reset state if file is removed
        if st.session_state.last_processed_file_id is not None:
            st.session_state.pages = []
            st.session_state.current_page = 0
            st.session_state.last_processed_file_id = None
            if "last_processed_image" in st.session_state:
                del st.session_state.last_processed_image
            if "last_original_image" in st.session_state:
                del st.session_state.last_original_image

if __name__ == "__main__":
    main()
