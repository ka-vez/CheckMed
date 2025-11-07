import os
from fastapi import FastAPI
from api import verify
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ChecMed Verification API")


API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise EnvironmentError("GEMINI_API_KEY environment variable not set.")

app.include_router(verify.router)




