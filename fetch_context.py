"""
fetch_context.py
Recopila el contexto actual desde GA4 y Google Trends.
Devuelve un dict que se pasa al modelo de predicción.
"""

import os
import json
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_ga4_top_topics(n=5):
    """
    Consulta GA4 y devuelve los temas (categorías de página) con más tráfico
    en los últimos 7 días.
    """
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange
        )
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GA4_CREDENTIALS_JSON"),
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=os.getenv("GA4_PROPERTY_ID"),
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
            dimensions=[Dimension(name="pageCategory")],
            metrics=[Metric(name="screenPageViews")],
            limit=n,
        )
        response = client.run_report(request)

        topics = []
        for row in response.rows:
            topics.append({
                "categoria": row.dimension_values[0].value,
                "pageviews": int(row.metric_values[0].value),
            })
        return topics

    except Exception as e:
        print(f"[GA4] Error al consultar: {e}")
        # Fallback con datos ilustrativos si GA4 falla
        return [
            {"categoria": "Política regional", "pageviews": 48200},
            {"categoria": "Economía / precios", "pageviews": 39100},
            {"categoria": "Clima / medio ambiente", "pageviews": 31500},
            {"categoria": "Fútbol", "pageviews": 28900},
            {"categoria": "Salud", "pageviews": 21300},
        ]


def get_google_trends(keywords=None):
    """
    Consulta Google Trends para Chile y devuelve los temas en alza.
    """
    try:
        from pytrends.request import TrendReq

        if keywords is None:
            keywords = ["biobio", "noticias chile", "economia chile", "clima chile"]

        pytrends = TrendReq(hl="es-CL", tz=240)
        pytrends.build_payload(keywords[:5], geo="CL", timeframe="now 7-d")
        df = pytrends.interest_over_time()

        if df.empty:
            return []

        # Devuelve el promedio de interés de los últimos 7 días por keyword
        result = []
        for kw in keywords[:5]:
            if kw in df.columns:
                result.append({"keyword": kw, "interes_promedio": int(df[kw].mean())})
        return sorted(result, key=lambda x: x["interes_promedio"], reverse=True)

    except Exception as e:
        print(f"[Trends] Error al consultar: {e}")
        return []


def get_current_context():
    """
    Función principal. Devuelve el contexto completo del momento.
    Este dict se pasa directamente al prompt de predicción.
    """
    hoy = date.today()
    semana = hoy.isocalendar()[1]

    # Determinar temporada en hemisferio sur
    mes = hoy.month
    if mes in [12, 1, 2]:
        temporada = "verano"
    elif mes in [3, 4, 5]:
        temporada = "otoño"
    elif mes in [6, 7, 8]:
        temporada = "invierno"
    else:
        temporada = "primavera"

    context = {
        "fecha": hoy.strftime("%A %d de %B de %Y"),
        "semana_del_ano": semana,
        "temporada": temporada,
        "mes": hoy.strftime("%B"),
        # Indicadores económicos — actualizar manualmente o conectar a API del Banco Central
        "indicadores": {
            "ipc": "4.1%",        # Actualizar mensualmente
            "dolar": "$975",      # Puede conectarse a mindicador.cl
            "desempleo": "8.6%",  # Actualizar trimestralmente
        },
        "top_temas_ga4": get_ga4_top_topics(n=5),
        "tendencias_google": get_google_trends(),
        "region": "Biobío, Chile",
    }

    print(f"[Context] Contexto generado para semana {semana} / {temporada}")
    return context


if __name__ == "__main__":
    ctx = get_current_context()
    print(json.dumps(ctx, ensure_ascii=False, indent=2))
