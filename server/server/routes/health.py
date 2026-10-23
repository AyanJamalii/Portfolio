from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"status": "online", "message": "Ayan AI Portfolio API is running."}


@router.get("/health")
def health_check():
    return {"status": "healthy"}
