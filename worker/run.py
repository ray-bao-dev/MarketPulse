import asyncio

from marketpulse.services.sync import run_worker


if __name__ == "__main__":
    asyncio.run(run_worker())
