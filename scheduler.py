"""
scheduler.py
Configura el scheduler que ejecuta la predicción cada mañana a las 7:00 AM.
Se importa desde main.py al iniciar el servidor.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

scheduler = BackgroundScheduler(timezone=pytz.timezone("America/Santiago"))


def start_scheduler():
    from run_prediction import run_prediction

    scheduler.add_job(
        run_prediction,
        trigger=CronTrigger(hour=7, minute=0),  # 7:00 AM hora de Santiago
        id="prediccion_diaria",
        replace_existing=True,
    )

    scheduler.start()
    print("[Scheduler] Activo — predicción diaria a las 07:00 hora Santiago")
