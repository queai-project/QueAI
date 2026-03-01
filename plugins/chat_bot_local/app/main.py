from fastapi import FastAPI
from langchain_ollama import ChatOllama
from app.core.config import settings
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Chat Bot Ollama",root_path="/api/chatbot_local")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM = ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_SERVER, temperature=settings.OLLAMA_TEMPERATURE)

@app.post("/message")
def send_message(message: str):
    response = LLM.invoke(message)
    return {"response": response.content}

@app.get("/health")
def health_check():
    return {"status": "healthy" , "model":settings.OLLAMA_MODEL, "serve": settings.OLLAMA_SERVER,"temperature":settings.OLLAMA_TEMPERATURE}

# Servir los archivos estáticos de la UI
app.mount("/ui", StaticFiles(directory="frontend_dist", html=True), name="ui")