import streamlit as st
import os
import tempfile
from pathlib import Path
import subprocess
from googletrans import Translator
from gtts import gTTS
import base64

try:
    import whisper
except ImportError:
    st.error("Please install the correct whisper package using: pip install -U openai-whisper")
    st.stop()

def check_ffmpeg():
    """Check if ffmpeg is installed and accessible"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def load_model():
    try:
        model = whisper.load_model("base")
        return model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

def translate_to_tamil(text):
    try:
        translator = Translator()
        translation = translator.translate(text, dest='ta')
        return translation.text
    except Exception as e:
        return f"Translation error: {str(e)}"

def text_to_speech(text):
    try:
        # Create Tamil speech
        tts = gTTS(text=text, lang='ta', slow=False)
        
        # Save to a temporary file
        speech_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(speech_file.name)
        return speech_file.name
    except Exception as e:
        return f"Speech generation error: {str(e)}"

def transcribe_audio(model, audio_path):
    try:
        if not os.path.exists(audio_path):
            return "Error: Audio file not found"
        if os.path.getsize(audio_path) == 0:
            return "Error: Audio file is empty"
        result = model.transcribe(audio_path, language="en")
        return result["text"]
    except Exception as e:
        return f"Error during transcription: {str(e)}"

def main():
    st.title("English to Tamil Audio Translator")
    st.write("Upload English audio to get Tamil translation and speech")
    
    if not check_ffmpeg():
        st.error("FFmpeg is not installed. Please install FFmpeg to use this application.")
        st.stop()
    
    # Load model
    @st.cache_resource
    def get_model():
        return load_model()
    
    model = get_model()
    if model is None:
        st.error("Failed to load the transcription model.")
        st.stop()
    
    # File uploader
    audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'])
    
    if audio_file is not None:
        # Create temporary file for uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp_file:
            tmp_file.write(audio_file.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            if st.button("Translate and Speak"):
                with st.spinner("Processing..."):
                    # Step 1: Transcribe English audio to text
                    english_text = transcribe_audio(model, tmp_file_path)
                    if english_text.startswith("Error"):
                        st.error(english_text)
                        st.stop()
                    
                    # Display English transcription
                    st.subheader("English Transcription:")
                    st.write(english_text)
                    
                    # Step 2: Translate to Tamil
                    tamil_text = translate_to_tamil(english_text)
                    if tamil_text.startswith("Translation error"):
                        st.error(tamil_text)
                        st.stop()
                    
                    # Display Tamil translation
                    st.subheader("Tamil Translation:")
                    st.write(tamil_text)
                    
                    # Step 3: Convert Tamil text to speech
                    tamil_speech_file = text_to_speech(tamil_text)
                    if tamil_speech_file.startswith("Speech generation error"):
                        st.error(tamil_speech_file)
                        st.stop()
                    
                    # Display audio player
                    st.subheader("Tamil Audio:")
                    with open(tamil_speech_file, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/mp3')
                    
                    # Add download button for Tamil audio
                    with open(tamil_speech_file, "rb") as file:
                        st.download_button(
                            label="Download Tamil Audio",
                            data=file,
                            file_name="tamil_translation.mp3",
                            mime="audio/mp3"
                        )
        
        finally:
            # Clean up temporary files
            try:
                Path(tmp_file_path).unlink()
                if 'tamil_speech_file' in locals():
                    Path(tamil_speech_file).unlink()
            except:
                pass

    # Add instructions in sidebar
    with st.sidebar:
        st.header("Instructions")
        st.write("""
        1. Upload an English audio file
        2. Click 'Translate and Speak'
        3. Wait for processing
        4. Use the audio player to listen to Tamil translation
        5. Download the Tamil audio if needed
        """)

if __name__ == "__main__":
    main()