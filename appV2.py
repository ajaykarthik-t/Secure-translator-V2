import streamlit as st
import os
import tempfile
from pathlib import Path
import subprocess
from googletrans import Translator
from gtts import gTTS
import base64
from cryptography.fernet import Fernet
import io

try:
    import whisper
except ImportError:
    st.error("Please install the correct whisper package using: pip install -U openai-whisper")
    st.stop()

def generate_key():
    """Generate an encryption key"""
    return Fernet.generate_key()

def encrypt_file(file_bytes, key):
    """Encrypt file using Fernet symmetric encryption"""
    f = Fernet(key)
    return f.encrypt(file_bytes)

def decrypt_file(encrypted_data, key):
    """Decrypt file using Fernet symmetric encryption"""
    try:
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    except Exception as e:
        return None

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
        tts = gTTS(text=text, lang='ta', slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return audio_fp.getvalue()
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
    st.title("Secure English to Tamil Audio Translator")
    
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

    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Standard Translation", "Secure Translation", "Decrypt Audio"])

    # Tab 1: Standard Translation
    with tab1:
        st.header("Standard Translation")
        audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'], key="standard")
        
        if audio_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp_file:
                tmp_file.write(audio_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                if st.button("Translate and Speak"):
                    with st.spinner("Processing..."):
                        english_text = transcribe_audio(model, tmp_file_path)
                        if english_text.startswith("Error"):
                            st.error(english_text)
                            st.stop()
                        
                        st.subheader("English Transcription:")
                        st.write(english_text)
                        
                        tamil_text = translate_to_tamil(english_text)
                        if tamil_text.startswith("Translation error"):
                            st.error(tamil_text)
                            st.stop()
                        
                        st.subheader("Tamil Translation:")
                        st.write(tamil_text)
                        
                        audio_bytes = text_to_speech(tamil_text)
                        if isinstance(audio_bytes, str) and audio_bytes.startswith("Speech generation error"):
                            st.error(audio_bytes)
                            st.stop()
                        
                        st.subheader("Tamil Audio:")
                        st.audio(audio_bytes, format='audio/mp3')
                        
                        st.download_button(
                            label="Download Tamil Audio",
                            data=audio_bytes,
                            file_name="tamil_translation.mp3",
                            mime="audio/mp3"
                        )
            
            finally:
                try:
                    Path(tmp_file_path).unlink()
                except:
                    pass

    # Tab 2: Secure Translation
    with tab2:
        st.header("Secure Translation")
        secure_audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'], key="secure")
        
        if secure_audio_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(secure_audio_file.name).suffix) as tmp_file:
                tmp_file.write(secure_audio_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                if st.button("Translate and Encrypt"):
                    with st.spinner("Processing..."):
                        # Generate encryption key
                        key = generate_key()
                        
                        # Transcribe and translate
                        english_text = transcribe_audio(model, tmp_file_path)
                        if english_text.startswith("Error"):
                            st.error(english_text)
                            st.stop()
                        
                        tamil_text = translate_to_tamil(english_text)
                        if tamil_text.startswith("Translation error"):
                            st.error(tamil_text)
                            st.stop()
                        
                        # Generate audio
                        audio_bytes = text_to_speech(tamil_text)
                        if isinstance(audio_bytes, str) and audio_bytes.startswith("Speech generation error"):
                            st.error(audio_bytes)
                            st.stop()
                        
                        # Encrypt audio
                        encrypted_audio = encrypt_file(audio_bytes, key)
                        
                        # Display key
                        st.warning("⚠️ Save this decryption key - you'll need it to play the audio:")
                        st.code(key.decode(), language="text")
                        
                        # Download encrypted audio
                        st.download_button(
                            label="Download Encrypted Tamil Audio",
                            data=encrypted_audio,
                            file_name="encrypted_tamil_translation.enc",
                            mime="application/octet-stream"
                        )
            
            finally:
                try:
                    Path(tmp_file_path).unlink()
                except:
                    pass

    # Tab 3: Decrypt Audio
    with tab3:
        st.header("Decrypt Audio")
        encrypted_file = st.file_uploader("Upload encrypted audio file", type=['enc'], key="decrypt")
        key_input = st.text_input("Enter decryption key", type="password")
        
        if encrypted_file is not None and key_input:
            try:
                # Decrypt audio
                encrypted_data = encrypted_file.read()
                decrypted_audio = decrypt_file(encrypted_data, key_input.encode())
                
                if decrypted_audio is None:
                    st.error("Invalid decryption key or corrupted file")
                else:
                    st.success("File decrypted successfully!")
                    st.audio(decrypted_audio, format='audio/mp3')
                    
                    st.download_button(
                        label="Download Decrypted Audio",
                        data=decrypted_audio,
                        file_name="decrypted_tamil_translation.mp3",
                        mime="audio/mp3"
                    )
            except Exception as e:
                st.error(f"Decryption error: Invalid key or corrupted file")

if __name__ == "__main__":
    main()