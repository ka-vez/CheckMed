# local imports
import os
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# external imports
from api import verify, report

load_dotenv()

app = FastAPI(
    title="CheckMed Verification API",
    description="""
    **CheckMed** is a pharmaceutical verification API that uses AI to authenticate medications 
    and detect counterfeit drugs.
    
    ## Features
    
    * **NAFDAC Number Verification** - Validates official drug registration numbers
    * **Package Inspection** - Compares user-uploaded packaging against verified golden standards
    * **Image Analysis** - Uses Google's Gemini AI to detect visual discrepancies
    * **Multi-stage Verification** - Sequential checks for comprehensive authentication
    
    ## How It Works
    
    1. Upload images of the medication (packaging, blister packs)
    2. Provide the drug name and NAFDAC number
    3. Receive instant HIGH-RISK or VERIFIED status with detailed reasoning
    
    This API helps protect consumers from counterfeit medications by leveraging computer vision 
    and multi-modal AI models to verify product authenticity.
    """,
    version="1.0.0",
    contact={
        "name": "CheckMed Team",
    }
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise EnvironmentError("GEMINI_API_KEY environment variable not set.")

app.include_router(verify.router)
app.include_router(report.router)




