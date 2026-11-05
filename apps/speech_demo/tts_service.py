import torch
from transformers import VitsModel, AutoTokenizer
import scipy.io.wavfile
import io
import numpy as np

# Load model dan tokenizer (dilakukan sekali saat startup)
print("Loading TTS model...")
model = VitsModel.from_pretrained("facebook/mms-tts-ind")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-ind")
print("TTS model loaded successfully!")

def generate_speech(text):
    """
    Generate speech dari text
    
    Args:
        text: string text yang akan di-convert ke speech
    
    Returns:
        bytes: audio data dalam format WAV
    """
    try:
        # Tokenize text
        inputs = tokenizer(text, return_tensors="pt")
        
        # Generate audio
        with torch.no_grad():
            output = model(**inputs).waveform
        
        # Convert tensor ke numpy array
        audio_array = output.squeeze().cpu().numpy()
        
        # Normalize audio ke range -1 to 1
        audio_array = audio_array / np.max(np.abs(audio_array))
        
        # Convert ke int16 untuk WAV format
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        # Save ke bytes
        byte_io = io.BytesIO()
        
        # Sample rate untuk model ini adalah 16000
        sample_rate = model.config.sampling_rate
        
        # Write WAV file ke BytesIO
        scipy.io.wavfile.write(byte_io, sample_rate, audio_int16)
        
        # Get bytes
        audio_bytes = byte_io.getvalue()
        
        return audio_bytes
    
    except Exception as e:
        print(f"Error in speech synthesis: {str(e)}")
        raise e