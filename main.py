"""
main.py
Servidor FastAPI del Predictor BioBioChile.
Expone las predicciones y recibe el feedback del equipo editorial.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from database import get_latest_prediction, save_feedback, get_feedback_history
from scheduler import start_scheduler

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al iniciar el servidor
    start_scheduler()
    yield
    # Al apagar el servidor


app = FastAPI(
    title="BioBioChile Predictor API",
    version="1.0.0",
    lifespan=lifespan,
)

# Permitir solicitudes desde el frontend en Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://biobiochile-predictor.vercel.app",  # ← reemplazar con tu URL real de Vercel
        "http://localhost:5173",                        # desarrollo local
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Modelos de request ───────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    tema: str
    estado: str   # 'usado' | 'descartado' | 'pendiente'
    nota: str = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "servicio": "BioBioChile Predictor API v1.0"}


@app.get("/predicciones")
def get_predicciones():
    """
    Devuelve la predicción más reciente.
    El frontend llama a este endpoint cada 5 minutos.
    """
    data = get_latest_prediction()
    if not data:
        raise HTTPException(status_code=404, detail="No hay predicciones disponibles aún.")
    return data


@app.post("/predicciones/generar")
def generar_prediccion_manual():
    """
    Genera una predicción de forma manual (sin esperar al scheduler).
    Útil para pruebas o para el primer arranque.
    """
    from run_prediction import run_prediction
    result = run_prediction()
    if not result:
        raise HTTPException(status_code=500, detail="Error al generar predicción.")
    return result


@app.post("/feedback")
def post_feedback(body: FeedbackRequest):
    """
    Recibe el feedback del equipo editorial sobre una predicción.
    """
    if body.estado not in ("usado", "descartado", "pendiente"):
        raise HTTPException(status_code=400, detail="estado debe ser: usado, descartado o pendiente")
    ok = save_feedback(body.tema, body.estado, body.nota)
    if not ok:
        raise HTTPException(status_code=500, detail="Error al guardar feedback.")
    return {"ok": True, "tema": body.tema, "estado": body.estado}


@app.get("/feedback/historial")
def get_historial():
    """Devuelve el historial de feedback para revisión."""
    return get_feedback_history(limit=100)


@app.get("/health")
def health():
    """Railway usa este endpoint para verificar que el servidor está vivo."""
    return {"status": "ok"}
