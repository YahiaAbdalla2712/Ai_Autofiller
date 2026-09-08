from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from Intent_parser import run_intent_parser
from pydantic import BaseModel

app = FastAPI(title="AutoFiller Parser API")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class IntentRequest(BaseModel):
    message: str
    current_data: dict
    schema: dict
    history:list[dict] = []


@app.post("/intent")
def process_intent(request: IntentRequest):
    print("\n========== REQUEST ==========")
    print("MESSAGE:")
    print(request.message)

    print("\nCURRENT DATA:")
    print(request.current_data)

    print("\nSCHEMA:")
    print(request.schema)

    print("=============================\n")

    result = run_intent_parser(
        user_input = request.message,
        current_data = request.current_data,
        schema = request.schema,
        history = request.history
    )

    return result


@app.get("/")
def root():
    return FileResponse("frontend/index.html")