"""Cron-style scheduler around the pipeline.

Production schedule is the 1st of every month at 06:00. For local
testing / screenshots, temporarily switch to CronTrigger(minute="*/2")
so it fires every two minutes. Don't forget to switch back before
pushing.
"""

import logging
import os
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.append(os.path.dirname(__file__))
from run_pipeline import main as run_pipeline  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

scheduler = BlockingScheduler()

scheduler.add_job(
    func=run_pipeline,
    trigger=CronTrigger(day=1, hour=6, minute=0),
    id="monthly_regulatory_report",
    name="Monthly Regulatory Report",
    # 1-hour grace window in case the host was down at 06:00.
    misfire_grace_time=3600,
)


if __name__ == "__main__":
    print("Scheduler running. Pipeline fires on the 1st of each month at 06:00.")
    print("Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
