from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from backend.retrieval import get_qa_chain, add_document_to_index
import os
import shutil
import uuid
from azure.storage.blob import BlobServiceClient

load_dotenv()

print("AZURE_STORAGE_CONNECTION_STRING:", os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
print("AZURE_STORAGE_CONTAINER_NAME:", os.getenv("AZURE_STORAGE_CONTAINER_NAME"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    temp_path = None
    try:
        print(f"Starting upload for file: {file.filename}")
        # Save uploaded file to disk
        file_id = str(uuid.uuid4())
        temp_path = f"temp_{file_id}_{file.filename}"
        print(f"Saving file to: {temp_path}")
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        print("File saved successfully, starting indexing...")

        # Upload to Azure Blob Storage
        AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
        if not AZURE_STORAGE_CONNECTION_STRING or not AZURE_STORAGE_CONTAINER_NAME:
            raise ValueError("Azure Storage connection string or container name is missing in .env file.")
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=file.filename)
        with open(temp_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        print(f"Uploaded {file.filename} to Azure Blob Storage in container {AZURE_STORAGE_CONTAINER_NAME}")

        # Process and add document to Azure Search index
        success = add_document_to_index(temp_path, file.filename)
        if success:
            print("Document indexed successfully")
            os.remove(temp_path)  # Delete the temp file after indexing and upload
            return {"filename": file.filename, "status": "Uploaded to Azure Blob Storage and indexed successfully"}
        else:
            print("Failed to index document")
            os.remove(temp_path)
            return JSONResponse(status_code=500, content={"error": "Failed to index document"})
    except Exception as e:
        print(f"Upload error: {str(e)}")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(status_code=500, content={"error": f"Upload failed: {str(e)}"})

@app.post("/ask")
async def ask_question(data: dict):
    question = data.get("question")
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question is required"})

    try:
        # Check if required environment variables are set
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY", 
            "AZURE_OPENAI_CHAT_DEPLOYMENT",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            "AZURE_SEARCH_INDEX_NAME",
            "AZURE_SEARCH_ENDPOINT",
            "AZURE_SEARCH_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            return JSONResponse(
                status_code=500, 
                content={
                    "error": f"Missing environment variables: {', '.join(missing_vars)}. Please create a .env file with your Azure credentials."
                }
            )
        
        qa_chain = get_qa_chain()
        result = qa_chain.invoke({"query": question})
        return {"answer": result["result"]}
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
