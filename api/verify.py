# internal imports 
import json
import base64  
import asyncio 
from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from google import genai
from google.genai import types
from dotenv import load_dotenv

# external imports
from config.system_prompts import OCR_CLERK, PACKAGE_INSPECTOR, BLISTER_PACK_CHECK


load_dotenv()
client = genai.Client()
router = APIRouter(prefix="/api/verify", tags=["verify"])

golden_standards = {
    "artcin": {
        "text_data": {
            "type": "tablet",
            "nafdac_number": "04-4213",
            "manufacturer": "Yangzhou No. 3 Pharmaceutical Co., Ltd."
        },
        "golden_box_image_path": "medicine_images/artcin/artcin_package.jpg",
        "golden_blister_image_path": "medicine_images/artcin/artcin_blister_pack.jpg"
    },

    "nasodyne": {
        "text_data": {
            "type": "syrup",
            "nafdac_number": "A11-1161",
            "manufacturer": "May & Baker Nigeria PLC"
        },
        "golden_box_image_path": "medicine_images/nasodyne/nasodyne_package.jpg"
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
        print(response)
        ai_response_text = response.text
        
        if not ai_response_text:
            raise HTTPException(status_code=502, detail="Gemini returned empty response")
        
        return json.loads(ai_response_text)
    except Exception as e:
        print(f"Gemini SDK error: {e}")
        raise HTTPException(status_code=502, detail=f"Gemini API error: {str(e)}")


# --- 5. Your Single API Endpoint (UPDATED) ---

@router.post("/verify")
async def verify_drug(
    # Instead of a BaseModel, we now define the form fields one by one.
    drug_name: str = Form(...),
    nafdac_number: str = Form(...),
    box_image: UploadFile = File(...),
    blister_pack_image: UploadFile | None = File(None)
):
    """
    The main verification endpoint. Accepts multipart/form-data.
    """
    
    # 1. Get the "Golden Standard" data
    golden_data = golden_standards.get(drug_name.lower())
    if not golden_data:
        raise HTTPException(status_code=404, detail="Drug not found in our MVP database.")
    
    # 1.5. Read the golden standard images from disk
    try:
        with open(golden_data["golden_box_image_path"], "rb") as f:
            golden_box_bytes = f.read()
        
        # Optional: read blister if path exists
        golden_blister_pack_bytes = None
        if "golden_blister_image_path" in golden_data:
            with open(golden_data["golden_blister_image_path"], "rb") as f:
                golden_blister_pack_bytes = f.read()
    except FileNotFoundError as e:
        print(f"Golden image not found: {e}")
        raise HTTPException(status_code=500, detail=f"Golden standard image not found: {str(e)}")
    except Exception as e:
        print(f"Error reading golden images: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading golden images: {str(e)}")
    
    
    # 2. Read the *user's* uploaded files into bytes
    try:
        box_image_bytes = await box_image.read()
        
        # Handle optional blister pack image
        blister_pack_image_bytes = None
        if blister_pack_image:
            blister_pack_image_bytes = await blister_pack_image.read()
    except Exception as e:
        print(f"File read error: {e}")
        raise HTTPException(status_code=400, detail="Error reading uploaded files.")
    
    try:
        # --- CALL 1 (REPLACED): Direct NAFDAC number check (no model call) ---
        # Use the user-supplied nafdac_number form field and compare against the golden standard.
        user_nafdac = (nafdac_number or "").strip()
        golden_nafdac = (golden_data.get("text_data", {}).get("nafdac_number") or "").strip()
        if not golden_nafdac:
            raise HTTPException(status_code=500, detail="Golden standard missing NAFDAC number.")
        if user_nafdac != golden_nafdac:
            message =  {
                "status": "HIGH-RISK",
                "reason": "NAFDAC number mismatch",
                "expected_nafdac": golden_nafdac,
                "provided_nafdac": user_nafdac
            }

            raise HTTPException(status_code=404, detail=message)

        # Passed the NAFDAC check
        print({"status": "OK", "reason": "NAFDAC number matches"})

        # --- CALL 2: The "Package Inspector" (Box Check) ---
        system_prompt_2 = PACKAGE_INSPECTOR
        contents_2 = [
            "GENUINE Box",
            types.Part.from_bytes(
                data=golden_box_bytes, 
                mime_type="image/jpeg"
            ),
            "USER'S Box. Compare this to the GENUINE Box.",
            types.Part.from_bytes(
                data=box_image_bytes, 
                mime_type=box_image.content_type or "image/jpeg"
            )
        ]
        call_2_result = await run_gemini_call(system_prompt_2, contents_2)
        if call_2_result.get("status") == "HIGH-RISK":
            raise HTTPException(status_code=404, detail=call_2_result)

        # passed Package Inspector Check
        print(call_2_result)

        if golden_data['text_data']['type'] == "tablet":
            # --- CALL 3: The "Pharmacist" (Blister Pack) ---
            # Ensure we actually have the golden blister and the user's blister bytes before passing to from_bytes
            if golden_blister_pack_bytes is None:
                raise HTTPException(status_code=500, detail="Golden blister image not available for this product.")
            if blister_pack_image_bytes is None:
                raise HTTPException(status_code=400, detail="User blister pack image not provided.")
    
            system_prompt_3 = BLISTER_PACK_CHECK
            contents_3 = [
                "GENUINE Blister Pack",
                types.Part.from_bytes(
                    data=golden_blister_pack_bytes,
                    mime_type="image/jpeg"
                ),
                "USER'S Blister Pack. Compare this to the GENUINE Blister Pack",
                types.Part.from_bytes(
                    data=blister_pack_image_bytes,
                    mime_type=(getattr(blister_pack_image, "content_type", None) or "image/jpeg")
                )
            ]
            call_3_result = await run_gemini_call(system_prompt_3, contents_3)
            if call_3_result.get("status") == "HIGH-RISK":
                raise HTTPException(status_code=404, detail=call_3_result)
            
            print(call_3_result)

        # --- 6. All Checks Passed ---
        return {"status": "VERIFIED", "reason": "All checks passed."}

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Main endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")