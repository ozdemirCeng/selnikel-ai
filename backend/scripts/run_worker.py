"""
Selnikel AI — Background Ingestion Worker CLI Runner.
Usage:
    python -m scripts.run_worker --poll-interval 2.0
"""
import argparse
import asyncio
import signal
from app.core.logging import logger, setup_logging
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.ingestion.worker import IngestionWorkerDaemon

async def main():
    parser = argparse.ArgumentParser(description="Selnikel AI Ingestion Worker Daemon")
    parser.add_argument("--worker-id", type=str, default=None, help="Unique worker ID")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    args = parser.parse_args()

    setup_logging()
    settings.validate_auth_configuration()

    daemon = IngestionWorkerDaemon(
        worker_id=args.worker_id,
        poll_interval_seconds=args.poll_interval
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, daemon.stop)
        except NotImplementedError:
            pass  # Windows signal handling fallback

    logger.info(f"Starting standalone Ingestion Worker Process [{daemon.worker_id}]...")
    await daemon.start(AsyncSessionLocal)

if __name__ == "__main__":
    asyncio.run(main())
