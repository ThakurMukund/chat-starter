from fastapi import APIRouter
from prometheus_client import Counter


router = APIRouter()


REQUESTS = Counter('http_requests_total', 'Total HTTP Requests', ['path'])


@router.get("/health")
async def health():
    REQUESTS.labels(path='/health').inc()
    return {"status":"ok"}