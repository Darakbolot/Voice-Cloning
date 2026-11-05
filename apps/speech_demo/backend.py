from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import io
from pathlib import Path
from stt_service import transcribe_audio
from tts_service import generate_speech

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with (BASE_DIR / "templates" / "index.html").open("r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    Endpoint untuk melakukan speech-to-text
    """
    try:
        # Baca audio file
        audio_bytes = await audio.read()

        # Proses transcription
        transcription = transcribe_audio(audio_bytes)

        return {"transcription": transcription, "success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/synthesize")
async def synthesize(text: str):
    """
    Endpoint untuk melakukan text-to-speech
    """
    try:
        # Generate speech dari text
        audio_data = generate_speech(text)

        # Return sebagai audio stream
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=output.wav"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
