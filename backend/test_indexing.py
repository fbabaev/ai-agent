import os
from dotenv import load_dotenv
from retrieval import add_document_to_index

# Load environment variables
load_dotenv()

def test_document_indexing():
    print("Testing document indexing...")
    
    # Create a test document
    test_content = """Subject: VPN keeps disconnecting

Hi team, the VPN drops connection every 15-20 minutes. It's becoming impossible to work remotely. Can someone look into this?

– Alice, Singapore"""
    
    # Save test document
    test_file_path = "test_vpn_document.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print(f"Created test document: {test_file_path}")
    print(f"Document content length: {len(test_content)} characters")
    
    # Test indexing
    print("\nTesting document indexing...")
    try:
        success = add_document_to_index(test_file_path, "test_vpn_document.txt")
        
        if success:
            print("✅ Document indexing successful!")
        else:
            print("❌ Document indexing failed!")
            
    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"Cleaned up test file: {test_file_path}")

if __name__ == "__main__":
    test_document_indexing() 