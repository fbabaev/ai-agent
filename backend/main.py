from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from backend.retrieval import get_qa_chain, add_document_to_index
import os
import shutil
import uuid
from azure.storage.blob import BlobServiceClient, ContainerClient
import json
from datetime import datetime

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

METADATA_FILE = os.path.join(os.path.dirname(__file__), '../uploaded_files/metadata.json')

# Helper to load metadata

def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return []
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Helper to save metadata

def save_metadata(metadata):
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

@app.get("/library")
def get_library():
    # List all blobs in Azure container
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    if not AZURE_STORAGE_CONNECTION_STRING or not AZURE_STORAGE_CONTAINER_NAME:
        return JSONResponse(status_code=500, content={"error": "Azure Storage connection string or container name is missing in .env file."})
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
    blobs = list(container_client.list_blobs())
    # Load custom titles from metadata.json
    metadata = load_metadata()
    title_map = {entry["filename"]: entry.get("title", entry["filename"]) for entry in metadata}
    result = []
    for blob in blobs:
        # Use blob's creation time if available, else last modified
        timestamp = None
        if hasattr(blob, 'creation_time') and blob.creation_time:
            timestamp = blob.creation_time.isoformat()
        elif hasattr(blob, 'last_modified') and blob.last_modified:
            timestamp = blob.last_modified.isoformat()
        else:
            timestamp = ""
        result.append({
            "filename": blob.name,
            "title": title_map.get(blob.name, blob.name),
            "timestamp": timestamp
        })
    return result

@app.put("/library/{filename}")
def update_title(filename: str, data: dict):
    new_title = data.get("title")
    if not new_title:
        return JSONResponse(status_code=400, content={"error": "Title is required"})
    metadata = load_metadata()
    for entry in metadata:
        if entry["filename"] == filename:
            entry["title"] = new_title
            save_metadata(metadata)
            return {"success": True}
    return JSONResponse(status_code=404, content={"error": "File not found"})

@app.delete("/library/{filename}")
def delete_file(filename: str):
    metadata = load_metadata()
    new_metadata = [entry for entry in metadata if entry["filename"] != filename]
    file_in_metadata = len(new_metadata) != len(metadata)
    if file_in_metadata:
        save_metadata(new_metadata)
    # Always try to delete from Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    if AZURE_STORAGE_CONNECTION_STRING and AZURE_STORAGE_CONTAINER_NAME:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=filename)
            blob_client.delete_blob(delete_snapshots="include")
        except Exception as e:
            # If the error is that the blob does not exist, treat as success
            if "BlobNotFound" in str(e):
                pass
            else:
                print(f"Error deleting blob from Azure: {e}")
                return JSONResponse(status_code=500, content={"error": f"Failed to delete blob from Azure: {str(e)}"})
    return {"success": True}

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
            # Save metadata
            metadata = load_metadata()
            now = datetime.now().isoformat()
            metadata.append({
                "filename": file.filename,
                "title": file.filename,
                "timestamp": now
            })
            save_metadata(metadata)
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
