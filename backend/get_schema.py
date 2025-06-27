import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()

def get_index_schema():
    print("Fetching Azure Search index schema...")
    
    # Get credentials
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    
    print(f"Search endpoint: {search_endpoint}")
    print(f"Index name: {index_name}")
    
    try:
        # Create search client
        credential = AzureKeyCredential(search_key)
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        
        # Get index properties
        index_properties = search_client._index_client.get_index(index_name)
        
        print("\n=== INDEX SCHEMA ===")
        print(f"Index name: {index_properties.name}")
        print(f"Fields:")
        
        for field in index_properties.fields:
            print(f"  - {field.name}: {field.type}")
            if hasattr(field, 'searchable') and field.searchable:
                print(f"    (searchable)")
            if hasattr(field, 'filterable') and field.filterable:
                print(f"    (filterable)")
            if hasattr(field, 'sortable') and field.sortable:
                print(f"    (sortable)")
            if hasattr(field, 'facetable') and field.facetable:
                print(f"    (facetable)")
            if hasattr(field, 'key') and field.key:
                print(f"    (key)")
        
        return index_properties.fields
        
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return None

if __name__ == "__main__":
    get_index_schema() 