import os
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, Form, UploadFile, BackgroundTasks, APIRouter
from pydantic import BaseModel, SecretStr
from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

# external imports 
from config.report_html import HTML

load_dotenv()

router = APIRouter(prefix='/api/report', tags=["report"])

# --- Email Configuration ---
# WARNING: This is complex and requires a real mail server.
# Do not do this during the hackathon.

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_EMAIL", ""),         # Your Gmail address
    MAIL_PASSWORD = SecretStr(os.getenv("MAIL_PASSWORD", "")),  # Gmail App Password
    MAIL_FROM = os.getenv("MAIL_EMAIL", ""),                 
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",                  # Changed from SendGrid to Gmail
    MAIL_FROM_NAME = "ChecMed Report",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

# --- HTML Email Template ---
# (See next section for the full HTML)
HTML_TEMPLATE = HTML
NAFDAC_EMAIL = os.getenv("NAFDAC_EMAIL")

# Development mode flag - set to False when email is configured
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ("true", "1", "yes")

# --- The New Report Endpoint (The "Real" Version) ---
@router.post("/")
async def send_report(
    background_tasks: BackgroundTasks,
    drug_name: str = Form(...),
    nafdac_number: str = Form(...),
    reason: str = Form(...),
    location: str = Form(...),
    box_image: UploadFile = File(...),
    blister_image: UploadFile | None = File(None)
):
    """
    Receives a report and sends it to NAFDAC via email.
    
    Args:
        drug_name: Name of the suspected counterfeit drug
        nafdac_number: NAFDAC registration number
        reason: Reason for the report
        location: Location where the drug was found
        box_image: Image of the drug packaging/box (required)
        blister_image: Image of blister pack (optional)
    """
    
    # Read box image bytes (required)
    box_image_bytes = await box_image.read()
    
    # Read blister image if provided
    blister_image_bytes = None
    if blister_image:
        blister_image_bytes = await blister_image.read()

    # Format the email body using the template
    try:
        html_body = HTML_TEMPLATE.format(
            drug_name=drug_name or "N/A",
            nafdac_number=nafdac_number or "N/A",
            reason=reason or "N/A",
            location=location or "N/A"
        )
    except KeyError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Email template error: missing placeholder {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error formatting email: {str(e)}"
        )

    # Validate NAFDAC email is configured
    if not NAFDAC_EMAIL:
        raise HTTPException(
            status_code=500,
            detail="NAFDAC email not configured. Set NAFDAC_EMAIL environment variable."
        )

    # Save images to temporary files (fastapi-mail needs file paths)
    temp_files = []
    try:
        # Save box image
        box_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb')
        box_temp.write(box_image_bytes)
        box_temp.close()
        temp_files.append(box_temp.name)
        
        # Save blister image if provided
        if blister_image_bytes:
            blister_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb')
            blister_temp.write(blister_image_bytes)
            blister_temp.close()
            temp_files.append(blister_temp.name)
    except Exception as e:
        # Clean up temp files on error
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Error preparing attachments: {str(e)}"
        )

    message = MessageSchema(
        subject="CRITICAL: Counterfeit Drug Report (ChecMed)",
        recipients=[NAFDAC_EMAIL], # type: ignore
        body=html_body,
        subtype=MessageType.html,
        attachments=temp_files  # fastapi-mail expects file paths
    )

    fm = FastMail(conf)
    
    # Background task to send email and cleanup temp files
    async def send_and_cleanup():
        try:
            if DEV_MODE:
                # Development mode: skip actual email sending, just log
                print("\n=== DEV MODE: Email Report (Not Sent) ===")
                print(f"To: {NAFDAC_EMAIL}")
                print(f"Subject: {message.subject}")
                print(f"Drug Name: {drug_name}")
                print(f"NAFDAC Number: {nafdac_number}")
                print(f"Reason: {reason}")
                print(f"Location: {location}")
                print(f"Attachments: {len(temp_files)} files")
                print("========================================\n")
            else:
                # Production mode: send actual email
                await fm.send_message(message)
                print(f"Email sent successfully to {NAFDAC_EMAIL}")
        except Exception as e:
            print(f"Error sending email: {str(e)}")
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    # Add to background tasks so the user isn't waiting
    background_tasks.add_task(send_and_cleanup)
    
    # Return an instant response to the user
    return JSONResponse(status_code=200, content={"message": "Report has been queued for sending."})