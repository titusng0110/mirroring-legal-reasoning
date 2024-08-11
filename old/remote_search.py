from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import *
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
import os

if __name__ == "__main__":
    load_dotenv(override=True)
    # setup text search client
    service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
    index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
    text_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    text_search_client = SearchClient(endpoint=service_endpoint, index_name=text_search_index_name, credential=index_creds)
    # setup embedding model
    embedding_client = AzureOpenAI(
        api_key = os.getenv("EMBEDDING_OPENAI_API_KEY"),
        api_version = os.getenv("EMBEDDING_OPENAI_API_VERSION"),
        azure_endpoint = os.getenv("EMBEDDING_OPENAI_API_ENDPOINT")
    )
    embedding_model = os.getenv("EMBEDDING_DEPLOYMENT_NAME")
    # get query and embed it
    query = input("Query: ")
    queryVector = embedding_client.embeddings.create(input = [query], model=embedding_model).data[0].embedding
    # search
    results = text_search_client.search(
        search_text=None,
        top=10,
        vector_queries=[VectorizedQuery(
            vector=queryVector,
            fields="contentVector",
            exhaustive=True,
            k_nearest_neighbors=10
        )]
    )
    for r in results:
        print("-" * 30)
        print(f"Title: {r['title']}")
        print(f"Content:\n{r['content']}")
        print()