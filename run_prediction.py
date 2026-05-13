"""
run_prediction.py
Toma el contexto actual, llama a Claude y guarda las predicciones en Supabase.
Este es el script que el scheduler ejecuta cada mañana.
"""

import os
import json
import anthropic
from datetime import date
from dotenv import load_dotenv
from fetch_context import get_current_context

load_dotenv()

SYSTEM_PROMPT = """Eres el sistema predictivo editorial de BioBioChile, medio regional líder en la región del Biobío, Chile.

Tu tarea es predecir qué temas y enfoques tendrán mayor interés para la audiencia en los próximos 7 días, basándote en el contexto que se te entrega.

Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta, sin texto adicional, sin backticks:

{
  "generado_el": "string con fecha y hora",
  "alerta": "string | null — solo si hay un tema urgente que podría explotar en los próximos días",
  "predicciones": [
    {
      "tema": "string — nombre del tema",
      "categoria": "string — categoría editorial",
      "confianza": número entre 0 y 100,
      "razon": "string — por qué es relevante ahora, máximo 2 oraciones",
      "enfoques": [
        {
          "enfoque": "string — ángulo específico",
          "titular_sugerido": "string — titular listo para usar"
        }
      ],
      "ventana_optima": "string — ej: martes o miércoles esta semana"
    }
  ]
}

Devuelve entre 4 y 6 predicciones ordenadas de mayor a menor confianza.
Sé específico para la audiencia regional del Biobío, no genérico."""


def run_prediction():
    """
    Ejecuta el ciclo completo: contexto → Claude → Supabase.
    Devuelve el resultado como dict.
    """
    print("[Predictor] Iniciando ciclo de predicción...")

    # 1. Obtener contexto real
    context = get_current_context()

    user_prompt = f"""Genera las predicciones editoriales para la semana {context['semana_del_ano']} del año.

Contexto actual:
- Fecha: {context['fecha']}
- Temporada: {context['temporada']} en el hemisferio sur
- Región: {context['region']}
- IPC: {context['indicadores']['ipc']}
- Dólar: {context['indicadores']['dolar']}
- Desempleo: {context['indicadores']['desempleo']}

Temas con más tráfico esta semana en BioBioChile (GA4):
{json.dumps(context['top_temas_ga4'], ensure_ascii=False, indent=2)}

Tendencias en Google Chile:
{json.dumps(context['tendencias_google'], ensure_ascii=False, indent=2)}

Genera las predicciones para los próximos 7 días."""

    # 2. Llamar a Claude
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text
        result = json.loads(raw)
        print(f"[Predictor] Claude generó {len(result.get('predicciones', []))} predicciones.")

    except json.JSONDecodeError as e:
        print(f"[Predictor] Error al parsear JSON de Claude: {e}")
        print(f"Raw response: {raw[:500]}")
        return None
    except Exception as e:
        print(f"[Predictor] Error al llamar a Claude: {e}")
        return None

    # 3. Guardar en Supabase
    result["fecha"] = date.today().isoformat()
    result["contexto"] = context
    _save_to_supabase(result)

    return result


def _save_to_supabase(result):
    """Guarda el resultado en la tabla 'predicciones' de Supabase."""
    try:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        supabase = create_client(url, key)

        row = {
            "fecha": result["fecha"],
            "generado_el": result.get("generado_el", ""),
            "alerta": result.get("alerta"),
            "predicciones": result["predicciones"],
            "contexto": result.get("contexto", {}),
        }

        response = supabase.table("predicciones").insert(row).execute()
        print(f"[Supabase] Guardado con id: {response.data[0]['id'] if response.data else 'N/A'}")

    except Exception as e:
        print(f"[Supabase] Error al guardar: {e}")


if __name__ == "__main__":
    result = run_prediction()
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
