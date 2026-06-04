"""scheduler.py - Run the regulatory pipeline on a schedule.

Production: 1st of every month at 06:00.
For demo screenshots: temporarily change to CronTrigger(minute='*/2').
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

# Production schedule: 1st of every month at 06:00.
# For demo: swap to CronTrigger(minute="*/2") to fire every 2 minutes,
# screenshot the terminal, then change back before pushing to GitHub.
scheduler.add_job(
    func=run_pipeline,
    trigger=CronTrigger(day=1, hour=6, minute=0),
    id="monthly_regulatory_report",
    name="Monthly Regulatory Report",
    misfire_grace_time=3600,  # 1-hour grace if the server was down
)


if __name__ == "__main__":
    print("Scheduler running - pipeline fires on the 1st of each month at 06:00")
    print("Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped cleanly.")
