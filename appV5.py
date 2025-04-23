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
import sounddevice as sd
import wave
import numpy as np
import whisper


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


def record_audio(file_path, duration=5, samplerate=44100):
    """Record audio for the specified duration."""
    # Convert progress to percentage for the progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Record audio
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype=np.int16)
    
    # Show progress while recording
    for i in range(duration):
        status_text.info(f"Recording... {i+1}/{duration} seconds")
        progress_bar.progress((i + 1) / duration)
        sd.sleep(1000)  # Sleep for 1 second
    
    sd.wait()  # Wait for recording to complete
    
    # Save the recording
    wave_file = wave.open(file_path, 'wb')
    wave_file.setnchannels(1)
    wave_file.setsampwidth(2)
    wave_file.setframerate(samplerate)
    wave_file.writeframes(recording.tobytes())
    wave_file.close()
    
    progress_bar.empty()
    status_text.success("Recording saved!")


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
        input_method = st.radio("Select Input Method", ["Upload Audio File", "Use Microphone"])

        if input_method == "Upload Audio File":
            audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'], key="standard")
        else:
            # Duration selection
            duration_options = {
                "5 seconds": 5,
                "10 seconds": 10,
                "30 seconds": 30,
                "1 minute": 60,
                "Custom duration": "custom"
            }
            
            selected_duration = st.selectbox(
                "Select recording duration",
                options=list(duration_options.keys())
            )
            
            # Handle custom duration input
            if selected_duration == "Custom duration":
                duration = st.number_input(
                    "Enter custom duration (seconds)",
                    min_value=1,
                    max_value=300,  # Maximum 5 minutes
                    value=30
                )
            else:
                duration = duration_options[selected_duration]
            
            st.write("Click the button below to start recording:")
            if st.button("Start Recording"):
                record_audio("recorded_audio.wav", duration=duration)
            
            if os.path.exists("recorded_audio.wav"):
                st.audio("recorded_audio.wav", format="audio/wav")

        target_lang = st.selectbox("Select target language", list(languages.keys()))

        if input_method == "Upload Audio File" and audio_file is not None:
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
                    st.audio(audio_bytes, format='audio/mp3')
                    st.download_button("Download Audio", data=audio_bytes, file_name=f"translation_{languages[target_lang]}.mp3", mime="audio/mp3")

            # Clean up temporary file
            os.unlink(tmp_file_path)

        if input_method == "Use Microphone" and os.path.exists("recorded_audio.wav"):
            if st.button("Translate Recorded Audio"):
                with st.spinner("Processing..."):
                    english_text = transcribe_audio(model, "recorded_audio.wav")
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
                    st.audio(audio_bytes, format='audio/mp3')
                    st.download_button("Download Audio", data=audio_bytes, file_name=f"translation_{languages[target_lang]}.mp3", mime="audio/mp3")

    with tab2:
        st.header("Secure Translation")
        audio_file = st.file_uploader("Choose an English audio file", type=['wav', 'mp3', 'm4a'], key="secure")
        
        if audio_file is not None:
            target_lang = st.selectbox("Select target language", list(languages.keys()), key="secure_lang")
            
            if st.button("Encrypt and Translate"):
                with st.spinner("Processing..."):
                    # Generate encryption key
                    key = generate_key()
                    
                    # Process and encrypt audio
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp_file:
                        tmp_file.write(audio_file.getvalue())
                        tmp_file_path = tmp_file.name
                        
                        # Transcribe and translate
                        english_text = transcribe_audio(model, tmp_file_path)
                        if english_text.startswith("Error"):
                            st.error(english_text)
                            st.stop()

                        translated_text = translate_text(english_text, languages[target_lang])
                        if translated_text.startswith("Translation error"):
                            st.error(translated_text)
                            st.stop()
                        
                        # Generate audio for translated text
                        audio_bytes = text_to_speech(translated_text, languages[target_lang])
                        
                        # Encrypt audio
                        encrypted_audio = encrypt_file(audio_bytes, key)
                        
                        # Display results
                        st.subheader("Encryption Key (Save this):")
                        st.code(base64.b64encode(key).decode())
                        
                        st.subheader("Encrypted Audio File:")
                        st.download_button(
                            "Download Encrypted Audio",
                            encrypted_audio,
                            "encrypted_audio.bin",
                            "application/octet-stream"
                        )
                        
                        st.subheader(f"{target_lang} Translation:")
                        st.write(translated_text)
                    
                    # Clean up temporary file
                    os.unlink(tmp_file_path)

    with tab3:
        st.header("Decrypt Audio")
        encrypted_file = st.file_uploader("Upload encrypted audio file", type=['bin'])
        encryption_key = st.text_input("Enter encryption key")
        
        if encrypted_file is not None and encryption_key:
            try:
                key = base64.b64decode(encryption_key)
                decrypted_data = decrypt_file(encrypted_file.getvalue(), key)
                
                if decrypted_data:
                    st.success("Decryption successful!")
                    st.audio(decrypted_data, format='audio/mp3')
                else:
                    st.error("Decryption failed. Please check your encryption key.")
            except Exception as e:
                st.error(f"Error during decryption: {str(e)}")


if __name__ == "__main__":
    main()