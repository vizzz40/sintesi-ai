from fastapi import FastAPI

app = FastAPI(title="Sintesi", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
