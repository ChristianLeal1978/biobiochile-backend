"""
database.py
Funciones de lectura y escritura en Supabase.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_supabase():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def get_latest_prediction():
    """Devuelve la predicción más reciente."""
    try:
        sb = get_supabase()
        response = (
            sb.table("predicciones")
            .select("*")
            .order("fecha", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[DB] Error al leer predicción: {e}")
        return None


def save_feedback(tema: str, estado: str, nota: str = None):
    """
    Guarda el feedback del equipo editorial.
    estado: 'usado' | 'descartado' | 'pendiente'
    """
    try:
        sb = get_supabase()
        row = {"tema": tema, "estado": estado, "nota": nota}
        sb.table("feedback").insert(row).execute()
        print(f"[DB] Feedback guardado: {tema} → {estado}")
        return True
    except Exception as e:
        print(f"[DB] Error al guardar feedback: {e}")
        return False


def get_feedback_history(limit=50):
    """Devuelve el historial de feedback para entrenar el modelo."""
    try:
        sb = get_supabase()
        response = (
            sb.table("feedback")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"[DB] Error al leer feedback: {e}")
        return []
