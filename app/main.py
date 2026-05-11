from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.file_controller import router as file_router
from app.controllers.bucket_controller import router as bucket_router
from app.controllers.broker_controller import router as broker_router
from app.controllers.image_process_controller import router as image_process_router

app = FastAPI(title="Mini Object Storage")

app = FastAPI(title="Mini Object Storage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(file_router)
app.include_router(bucket_router)
app.include_router(broker_router)
app.include_router(image_process_router)