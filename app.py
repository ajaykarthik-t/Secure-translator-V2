import streamlit as st
import os
import tempfile
from pathlib import Path

# Import whisper with error handling
try:
    import whisper
except ImportError:
    st.error("Please install the correct whisper package using: pip install -U openai-whisper")
    st.stop()

def load_model():
    try:
        # Load the Whisper model
        model = whisper.load_model("base")
        return model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

def transcribe_audio(model, audio_path):
    try:
        # Transcribe audio with Whisper
        result = model.transcribe(audio_path, language="en")
        return result["text"]
    except Exception as e:
        return f"Error during transcription: {str(e)}"

def main():
    st.title("American English Audio Transcription")
    st.write("Upload an audio file to get highly accurate American English transcription")
    
    # Load model on app startup
    @st.cache_resource
    def get_model():
        return load_model()
    
    # Check if model loaded successfully
    model = get_model()
    if model is None:
        st.error("Failed to load the transcription model. Please check your installation.")
        st.stop()
    
    # File uploader
    audio_file = st.file_uploader("Choose an audio file", type=['wav', 'mp3', 'm4a'])
    
    if audio_file is not None:
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio_file.name).suffix) as tmp_file:
            tmp_file.write(audio_file.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            # Add a button to trigger transcription
            if st.button("Transcribe Audio"):
                with st.spinner("Transcribing... This may take a few moments."):
                    # Get the transcription
                    transcription = transcribe_audio(model, tmp_file_path)
                    
                    if transcription.startswith("Error"):
                        st.error(transcription)
                    else:
                        # Display the transcription
                        st.header("Transcription")
                        st.write(transcription)
                        
                        # Option to download transcription
                        st.download_button(
                            label="Download Transcription",
                            data=transcription,
                            file_name="transcription.txt",
                            mime="text/plain"
                        )
                        
                        # Display model information
                        st.info("Whisper model used: base - Optimized for American English")
        
        finally:
            # Clean up the temporary file
            try:
                Path(tmp_file_path).unlink()
            except:
                pass

    # Add model selection
    with st.sidebar:
        st.header("About")
        st.write("""
        This app uses OpenAI's Whisper model, which is specifically trained on a diverse range of American English accents and speaking styles.
        
        The base model provides a good balance between accuracy and speed. For even higher accuracy, you can modify the code to use the 'medium' or 'large' model.
        """)

if __name__ == "__main__":
    main()