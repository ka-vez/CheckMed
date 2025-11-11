# internal imports 
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, File, Form, UploadFile, Depends
from sqlmodel import Session, select
from dotenv import load_dotenv

# external imports
from db.models import CreateMedicine
from db.database import get_session


load_dotenv()

router = APIRouter(prefix="/api/register-drug", tags=["register drug"])

# Create directory for storing medicine images if it doesn't exist
IMAGES_DIR = Path("medicine_images")
IMAGES_DIR.mkdir(exist_ok=True)


@router.post("/")
async def register_drug(
    drug_name: str = Form(...),
    drug_type: str = Form(...),
    nafdac_number: str = Form(...),
    manufacturer: str = Form(...),
    box_image: UploadFile = File(...),
    blister_pack_image: UploadFile | None = File(None),
    session: Session = Depends(get_session)
):
    """
    Register a new drug in the database with its golden standard images.
    
    Args:
        drug_name: Name of the drug (e.g., "artcin", "meprasil-20")
        drug_type: Type of drug formulation - must be either "syrup" or "tablet"
        nafdac_number: The NAFDAC registration number
        manufacturer: Manufacturer name
        box_image: Image of the drug packaging/box (required)
        blister_pack_image: Image of blister pack (optional, for tablets)
        session: Database session (injected)
    """
    
    # 1. Normalize and validate input
    drug_name_lower = drug_name.lower().strip()
    drug_type_lower = drug_type.lower().strip()
    
    # 2. Validate drug_type format
    valid_types = ["syrup", "tablet"]
    
    if drug_type_lower not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid drug type '{drug_type}'. Must be either 'syrup' or 'tablet'."
        )
    
    # 3. Check if drug already exists in database
    existing_drug = session.exec(
        select(CreateMedicine)
        .where(CreateMedicine.drug_name == drug_name_lower)
        .where(CreateMedicine.drug_type == drug_type_lower)
    ).first()
    
    if existing_drug:
        raise HTTPException(
            status_code=400,
            detail=f"Drug '{drug_name}' with type '{drug_type}' already exists in the database."
        )
    
    # 4. Create directory for this drug's images
    drug_dir = IMAGES_DIR / drug_name_lower
    drug_dir.mkdir(exist_ok=True)
    
    # 5. Save box image
    try:
        box_image_filename = f"{drug_name_lower}_package{Path(box_image.filename).suffix}"
        box_image_path = drug_dir / box_image_filename
        
        box_image_bytes = await box_image.read()
        with open(box_image_path, "wb") as f:
            f.write(box_image_bytes)
        
        golden_box_path = str(box_image_path)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving box image: {str(e)}"
        )
    
    # 6. Save blister pack image if provided
    golden_blister_path = None
    if blister_pack_image:
        try:
            blister_image_filename = f"{drug_name_lower}_blister_pack{Path(blister_pack_image.filename).suffix}"
            blister_image_path = drug_dir / blister_image_filename
            
            blister_image_bytes = await blister_pack_image.read()
            with open(blister_image_path, "wb") as f:
                f.write(blister_image_bytes)
            
            golden_blister_path = str(blister_image_path)
            
        except Exception as e:
            # Clean up box image if blister save fails
            try:
                os.unlink(box_image_path)
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Error saving blister pack image: {str(e)}"
            )
    
    # 7. Create database record
    try:
        new_medicine = CreateMedicine(
            drug_name=drug_name_lower,
            drug_type=drug_type_lower,
            nafdac_number=nafdac_number.strip(),
            manufacturer=manufacturer.strip(),
            golden_box_image_path=golden_box_path,
            golden_blister_image_path=golden_blister_path
        )
        
        session.add(new_medicine)
        session.commit()
        session.refresh(new_medicine)
        
        return {
            "status": "success",
            "message": f"Drug '{drug_name}' registered successfully",
            "data": {
                "id": new_medicine.id,
                "drug_name": new_medicine.drug_name,
                "drug_type": new_medicine.drug_type,
                "nafdac_number": new_medicine.nafdac_number,
                "manufacturer": new_medicine.manufacturer,
                "golden_box_image_path": new_medicine.golden_box_image_path,
                "golden_blister_image_path": new_medicine.golden_blister_image_path,
                "created_at": new_medicine.created_at.isoformat()
            }
        }
        
    except Exception as e:
        # Rollback and clean up files on database error
        session.rollback()
        try:
            os.unlink(box_image_path)
            if golden_blister_path:
                os.unlink(blister_image_path)
        except:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Error saving to database: {str(e)}"
        )