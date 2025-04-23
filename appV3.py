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
    return Fernet.generate_key()

def encrypt_file(file_bytes, key):
    f = Fernet(key)
    return f.encrypt(file_bytes)

def decrypt_file(encrypted_data, key):
    try:
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    except Exception:
        return None

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def load_model():
    try:
        return whisper.load_model("base")
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

def translate_text(text, lang_code):
    try:
        translator = Translator()
        translation = translator.translate(text, dest=lang_code)
        return translation.text
    except Exception as e:
        return f"Translation error: {str(e)}"

def text_to_speech(text, lang_code):
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return audio_fp.getvalue()
    except Exception as e:
        return f"Speech generation error: {str(e)}"

def transcribe_audio(model, audio_path):
    try:
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            return "Error: Invalid or empty audio file"
        result = model.transcribe(audio_path, language="en")
        return result["text"]
    except Exception as e:
        return f"Error during transcription: {str(e)}"

def main():
    st.title("Secure Multilingual Audio Translator")
    
    if not check_ffmpeg():
        st.error("FFmpeg is not installed. Please install FFmpeg to use this application.")
        st.stop()
    
    @st.cache_resource
    def get_model():
        return load_model()
    
    model = get_model()
    if model is None:
        st.error("Failed to load the transcription model.")
        st.stop()
    
    languages = {
        "Tamil": "ta",
        "Hindi": "hi",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Chinese (Simplified)": "zh-cn"
    }
    
    tab1, tab2, tab3 = st.tabs(["Standard Translation", "Secure Translation", "Decrypt Audio"])
    
    with tab1:
        st.header("Standard Translation")
        audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'], key="standard")
        target_lang = st.selectbox("Select target language", list(languages.keys()))
        
        if audio_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp_file:
                tmp_file.write(audio_file.getvalue())
                tmp_file_path = tmp_file.name
            
            if st.button("Translate and Speak"):
                with st.spinner("Processing..."):
                    english_text = transcribe_audio(model, tmp_file_path)
                    if english_text.startswith("Error"):
                        st.error(english_text)
                        st.stop()
                    
                    translated_text = translate_text(english_text, languages[target_lang])
                    if translated_text.startswith("Translation error"):
                        st.error(translated_text)
                        st.stop()
                    
                    st.subheader(f"{target_lang} Translation:")
                    st.write(translated_text)
                    
                    audio_bytes = text_to_speech(translated_text, languages[target_lang])
                    if isinstance(audio_bytes, str) and audio_bytes.startswith("Speech generation error"):
                        st.error(audio_bytes)
                        st.stop()
                    
                    st.audio(audio_bytes, format='audio/mp3')
                    st.download_button("Download Audio", data=audio_bytes, file_name=f"translation_{languages[target_lang]}.mp3", mime="audio/mp3")
    
    with tab2:
        st.header("Secure Translation")
        secure_audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'], key="secure")
        target_lang_secure = st.selectbox("Select target language", list(languages.keys()), key="secure_lang")
        
        if secure_audio_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(secure_audio_file.name).suffix) as tmp_file:
                tmp_file.write(secure_audio_file.getvalue())
                tmp_file_path = tmp_file.name
            
            if st.button("Translate and Encrypt"):
                with st.spinner("Processing..."):
                    key = generate_key()
                    english_text = transcribe_audio(model, tmp_file_path)
                    if english_text.startswith("Error"):
                        st.error(english_text)
                        st.stop()
                    
                    translated_text = translate_text(english_text, languages[target_lang_secure])
                    if translated_text.startswith("Translation error"):
                        st.error(translated_text)
                        st.stop()
                    
                    audio_bytes = text_to_speech(translated_text, languages[target_lang_secure])
                    if isinstance(audio_bytes, str) and audio_bytes.startswith("Speech generation error"):
                        st.error(audio_bytes)
                        st.stop()
                    
                    encrypted_audio = encrypt_file(audio_bytes, key)
                    st.warning("⚠️ Save this decryption key:")
                    st.code(key.decode(), language="text")
                    st.download_button("Download Encrypted Audio", data=encrypted_audio, file_name="encrypted_translation.enc", mime="application/octet-stream")
    
    with tab3:
        st.header("Decrypt Audio")
        encrypted_file = st.file_uploader("Upload encrypted audio file", type=['enc'], key="decrypt")
        key_input = st.text_input("Enter decryption key", type="password")
        
        if encrypted_file is not None and key_input:
            encrypted_data = encrypted_file.read()
            decrypted_audio = decrypt_file(encrypted_data, key_input.encode())
            
            if decrypted_audio is None:
                st.error("Invalid decryption key or corrupted file")
            else:
                st.success("File decrypted successfully!")
                st.audio(decrypted_audio, format='audio/mp3')
                st.download_button("Download Decrypted Audio", data=decrypted_audio, file_name="decrypted_translation.mp3", mime="audio/mp3")

if __name__ == "__main__":
    main()
