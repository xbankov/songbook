from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/about")
async def greet():
    return {"message": "Hello from FastAPI!"}


@app.get("/")
def read_root():
    return {"Hello": "World"}
