import os
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from uuid import uuid4
import datetime
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import mimetypes
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image

# Load environment variables
load_dotenv()

# Retrieve environment variables
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def add_document_to_index(file_path: str, filename: str):
    """Process a document and add it to the Azure Search index"""
    try:
        print(f"Reading document: {file_path}")
        # Detect file type
        mime_type, _ = mimetypes.guess_type(file_path)
        if filename.lower().endswith('.pdf') or (mime_type and 'pdf' in mime_type):
            print("Detected PDF file. Extracting text...")
            content = extract_text_from_pdf(file_path)
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif')) or (mime_type and mime_type.startswith('image/')):
            print("Detected image file. Extracting text with OCR...")
            try:
                image = Image.open(file_path)
                content = pytesseract.image_to_string(image)
            except Exception as e:
                print(f"Error extracting text from image: {e}")
                content = ""
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

        if not content.strip():
            print("No text extracted from file.")
            return False

        print(f"Document content length: {len(content)} characters")
        
        # Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Split text directly without Document objects
        chunks = text_splitter.split_text(content)
        
        print(f"Created {len(chunks)} chunks")
        
        print("Setting up embeddings...")
        
        # Set up embeddings
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            openai_api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_type="azure",
            api_version="2024-02-15-preview"
        )
        
        print("Adding documents to Azure Search...")
        
        docs = []
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            embedding = embeddings.embed_query(chunk)
            doc = {
                "id": str(uuid4()),
                "content": chunk,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": total_chunks,
                "content_vector": embedding,
                "country": "",
                "department": "",
                "date": datetime.datetime.now().isoformat(),
                "topic": ""
            }
            docs.append(doc)
        
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_SEARCH_KEY)
        )
        result = search_client.upload_documents(documents=docs)
        
        print("Documents added to Azure Search successfully")
        return True
        
    except Exception as e:
        print(f"Error adding document to index: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_qa_chain():
    # Set up the embedding model
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        openai_api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_type="azure",
        api_version="2024-02-15-preview"
    )

    # Connect to Azure Cognitive Search
    vectorstore = AzureSearch(
        azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
        azure_search_key=AZURE_SEARCH_KEY,
        index_name=AZURE_SEARCH_INDEX_NAME,
        embedding_function=embeddings.embed_query
    )

    # Initialize the retriever
    retriever = vectorstore.as_retriever()

    # Set up the GPT-4 model
    model = AzureChatOpenAI(
        deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT,
        openai_api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_type="azure",
        api_version="2024-02-15-preview"
    )

    # Combine retriever + LLM into a RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=model,
        retriever=retriever,
        return_source_documents=True  # Optional: to include sources in results
    )

    return qa_chain