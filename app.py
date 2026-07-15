import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List
from llama_cloud import LlamaCloud
import os

app = FastAPI(title="Invoice Extraction Service")

# Initialize client directly using your provided key
# Pass the raw string directly instead of using os.getenv
client = LlamaCloud(api_key="llx-knaUlGzQqxYtuAe9FnOO2YrMrjP2GXvmVycN5dQOtTA49XMX")

class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float
    amount: float

class InvoiceSchema(BaseModel):
    vendor_name: str
    invoice_number: str
    invoice_date: str
    line_items: List[LineItem]
    total_tax: float
    grand_total: float

@app.post("/extract")
async def extract_invoice(file: UploadFile = File(...)):
    # 1. Expand allowed extensions to include popular image formats
    filename_lower = file.filename.lower()
    
    if filename_lower.endswith('.pdf'):
        media_type = "application/pdf"
    elif filename_lower.endswith('.png'):
        media_type = "image/png"
    elif filename_lower.endswith(('.jpg', '.jpeg')):
        media_type = "image/jpeg"
    else:
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Only PDF, PNG, and JPEG formats are supported."
        )
    
    try:
        # Read the file data out of memory
        file_bytes = await file.read()
        
        # 2. Upload the file using the dynamically determined media type
        uploaded_file = client.files.create(
            file=(file.filename, file_bytes, media_type), 
            purpose="extract"
        )

        # 3. Trigger the extraction job matching the schema
        job = client.extract.create(
            file_input=uploaded_file.id,
            configuration={
                "data_schema": InvoiceSchema.model_json_schema(),
                "tier": "agentic",  # Essential for processing scattered photo/image layouts!
            },
        )

        # 4. Poll for completion
        while job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
            time.sleep(1.5)
            job = client.extract.get(job.id)

        if job.status == "COMPLETED":
            return job.extract_result
        else:
            raise HTTPException(status_code=500, detail=f"Extraction failed with status: {job.status}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))