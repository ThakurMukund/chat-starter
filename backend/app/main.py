import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError, AuthenticationError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from logging_config import logger
from ws_manager import manager
from api import router as api_router

load_dotenv()

app = FastAPI(title="chat-starter")

# === CONFIG ===
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/metrics")
async def metrics():
    return generate_latest()


# === MODEL HANDLERS ===
async def get_openai_response(prompt: str) -> str:
    if not client or not OPENAI_API_KEY:
        raise ValueError("Missing OpenAI API key")
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except (RateLimitError, AuthenticationError) as e:
        raise RuntimeError(f"OpenAI unavailable: {e}")
    except APIError as e:
        raise RuntimeError(f"OpenAI API error: {e}")


async def get_ollama_response(prompt: str) -> str:
    try:
        async with httpx.AsyncClient() as http_client:
            payload = {
                "model": OLLAMA_MODEL,
                "stream": False,  # 👈 disables streaming, returns full JSON
                "messages": [{"role": "user", "content": prompt}],
            }
            res = await http_client.post("http://host.docker.internal:11434/api/chat", json=payload, timeout=120)
            res.raise_for_status()
            data = res.json()
            # Ollama non-stream response: {'message': {'content': 'text...'}}
            return data.get("message", {}).get("content", "No response from Ollama.")
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"❌ Ollama error: {e}"


# === WEBSOCKET ===
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    global MODEL_PROVIDER
    await manager.connect(websocket, client_id)
    await websocket.send_text(f"✅ Connected. Current provider: {MODEL_PROVIDER.upper()}")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received from {client_id}: {data}")

            # --- SWITCH PROVIDER COMMAND ---
            if data.startswith("/use "):
                new_provider = data.replace("/use ", "").strip().lower()
                if new_provider in ["openai", "ollama"]:
                    MODEL_PROVIDER = new_provider
                    await websocket.send_text(f"🔄 Switched to {MODEL_PROVIDER.upper()} mode.")
                else:
                    await websocket.send_text("❌ Invalid provider. Use /use openai or /use ollama.")
                continue

            # --- MAIN CHAT FLOW ---
            try:
                if MODEL_PROVIDER == "openai":
                    response = await get_openai_response(data)
                else:
                    response = await get_ollama_response(data)
            except Exception as e:
                logger.warning(f"Error in {MODEL_PROVIDER}: {e}")
                # Automatically fallback to Ollama if OpenAI fails
                MODEL_PROVIDER = "ollama"
                await websocket.send_text(f"⚠️ OpenAI failed, switched to OLLAMA. ({e})")
                response = await get_ollama_response(data)

            await websocket.send_text(f"assistant: {response}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
