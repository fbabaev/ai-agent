import os
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings

# Load environment variables
load_dotenv()

def test_azure_connection():
    print("Testing Azure connection...")
    
    # Check environment variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "AZURE_SEARCH_INDEX_NAME",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_KEY"
    ]
    
    print("\nChecking environment variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the API key for security
            if "API_KEY" in var or "SEARCH_KEY" in var:
                print(f"✅ {var}: {'*' * 10}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: MISSING")
    
    # Test Azure OpenAI connection
    print("\nTesting Azure OpenAI connection...")
    try:
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_type="azure",
            api_version="2024-02-15-preview"
        )
        
        # Test embedding
        test_embedding = embeddings.embed_query("test")
        print(f"✅ Azure OpenAI connection successful - embedding length: {len(test_embedding)}")
        
    except Exception as e:
        print(f"❌ Azure OpenAI connection failed: {e}")
        return False
    
    # Test Azure Search connection
    print("\nTesting Azure Search connection...")
    try:
        from langchain_community.vectorstores import AzureSearch
        
        vectorstore = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key=os.getenv("AZURE_SEARCH_KEY"),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
            embedding_function=embeddings.embed_query
        )
        
        print("✅ Azure Search connection successful")
        
    except Exception as e:
        print(f"❌ Azure Search connection failed: {e}")
        return False
    
    print("\n✅ All Azure connections successful!")
    return True

if __name__ == "__main__":
    test_azure_connection() 