import os

import redis
from rq import Worker, Queue

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
QUEUES = ["default"]


if __name__ == "__main__":
    conn = redis.from_url(REDIS_URL)
    worker = Worker(queues=[Queue(name, connection=conn) for name in QUEUES], connection=conn)
    worker.work()
