from __future__ import annotations

from io import BytesIO

import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Appify Image Processing Node")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/image/grayscale")
async def grayscale(file: UploadFile = File(...)):
    raw = await file.read()
    img = Image.open(BytesIO(raw)).convert("RGB")
    arr = np.array(img)
    gray = arr.mean(axis=2).astype(np.uint8)
    out = Image.fromarray(gray, mode="L")
    buffer = BytesIO()
    out.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
