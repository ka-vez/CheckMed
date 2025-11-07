# internal imports 
import json
import base64  
import asyncio 
from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from google import genai
from google.genai import types
from dotenv import load_dotenv

# external imports
from config.system_prompts import OCR_CLERK, PACKAGE_INSPECTOR, PILL_CHECK


load_dotenv()
client = genai.Client()
router = APIRouter(prefix="/api/verify", tags=["verify"])


golden_standards = {
    "panadol": {
        "textData": {
            "nafdacNumber": "A11-0011",
            "manufacturer": "GSK Consumer Nigeria Plc"
        },
        "goldenBoxImage": "...YOUR_BASE64_STRING_FOR_REAL_PANADOL_BOX...",
        "goldenPillImage": "...YOUR_BASE64_STRING_FOR_REAL_PANADOL_PILL..."
    },
}



# --- 4. Reusable Gemini API Call Function ---
# (This function is identical to the previous version. It's perfect.)
async def run_gemini_call(system_prompt: str, contents: list) -> dict:
    """
    Sends a prompt (with text and image bytes) to the Gemini API
    using the official Python SDK.
    """
    try:
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=system_prompt),
        contents=contents
        
        )
        ai_response_text = response.text
        return json.loads(ai_response_text)
    except Exception as e:
        print(f"Gemini SDK error: {e}")
        raise HTTPException(status_code=502, detail=f"Gemini API error: {str(e)}")


# --- 5. Your Single API Endpoint (UPDATED) ---

@router.post("/verify")
async def verify_drug(
    # Instead of a BaseModel, we now define the form fields one by one.
    drug_name: str = Form(...),
    text_image: UploadFile = File(...),
    box_image: UploadFile = File(...),
    pill_image: UploadFile = File(...)
):
    """
    The main verification endpoint. Accepts multipart/form-data.
    """
    
    # 1. Get the "Golden Standard" data
    golden_data = golden_standards.get(drug_name.lower())
    if not golden_data:
        raise HTTPException(status_code=404, detail="Drug not found in our MVP database.")

    # 2. Decode *our* "golden" images from Base64
    try:
        golden_box_bytes = base64.b64decode(golden_data['goldenBoxImage'])
        golden_pill_bytes = base64.b64decode(golden_data['goldenPillImage'])
    except Exception as e:
        print(f"Server error: Golden image data is corrupt. {e}")
        raise HTTPException(status_code=500, detail="Server configuration error.")

    # 3. Read the *user's* uploaded files into bytes
    try:
        # This is a fast way to read all 3 files at the same time
        text_image_bytes, box_image_bytes, pill_image_bytes = await asyncio.gather(
            text_image.read(),
            box_image.read(),
            pill_image.read()
        )
    except Exception as e:
        print(f"File read error: {e}")
        raise HTTPException(status_code=400, detail="Error reading uploaded files.")

    try:
        # --- CALL 1: The "OCR Clerk" (Text Check) ---
        system_prompt_1 = OCR_CLERK
        contents_1 = [
            f"Here is the KNOWN-GOOD data: {json.dumps(golden_data['textData'])}",
            "Here is the user's image. Extract text and compare:",
            types.Part.from_bytes(data=text_image_bytes, mime_type=text_image.content_type)
        ]
        call_1_result = await run_gemini_call(system_prompt_1, contents_1)
        if call_1_result.get("status") == "HIGH-RISK":
            return call_1_result

        # --- CALL 2: The "Package Inspector" (Box Check) ---
        system_prompt_2 = PACKAGE_INSPECTOR
        contents_2 = [
            "Image 1: GENUINE Box",
            types.Part.from_bytes(data=golden_box_bytes, mime_type="image/jpeg"), # We know our golden type
            "Image 2: USER'S Box. Compare this to Image 1.",
            types.Part.from_bytes(data=box_image_bytes, mime_type=box_image.content_type)
        ]
        call_2_result = await run_gemini_call(system_prompt_2, contents_2)
        if call_2_result.get("status") == "HIGH-RISK":
            return call_2_result

        # --- CALL 3: The "Pharmacist" (Pill Check) ---
        system_prompt_3 = PILL_CHECK
        contents_3 = [
            "Image 1: GENUINE Pill",
            types.Part.from_bytes(data=golden_pill_bytes, mime_type="image/jpeg"), # We know our golden type
            "Image 2: USER'S Pill. Compare this to Image 1.",
            types.Part.from_bytes(data=pill_image_bytes, mime_type=pill_image.content_type)
        ]
        call_3_result = await run_gemini_call(system_prompt_3, contents_3)
        if call_3_result.get("status") == "HIGH-RISK":
            return call_3_result

        # --- 6. All Checks Passed ---
        return {"status": "VERIFIED", "reason": "All checks passed."}

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Main endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")