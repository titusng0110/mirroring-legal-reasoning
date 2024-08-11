from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from dotenv import load_dotenv
import os

load_dotenv(override=True)
service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
index_client = SearchIndexClient(service_endpoint, index_creds)

index = SearchIndex(
    name="casesrag",
    fields=[
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="title", type="Edm.String", analyzer_name="standard.lucene", 
                        filterable=True, sortable=True, facetable=True, searchable=True),
        # SearchField(name="titleVector", type="Collection(Edm.Single)",  
        #             hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
        #             vector_search_dimensions=1536, vector_search_profile_name="my-vector-config"),
        SearchableField(name="content", type="Edm.String", analyzer_name="standard.lucene",
                        filterable=True, sortable=True, facetable=True, searchable=True),
        SearchField(name="contentVector", type="Collection(Edm.Single)",  
                    hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
                    vector_search_dimensions=1536, vector_search_profile_name="my-vector-config"),
    ],
    vector_search=VectorSearch(
        profiles=[VectorSearchProfile(
            name="my-vector-config",
            algorithm_configuration_name="my-hnsw")
        ],
        algorithms=[
            HnswAlgorithmConfiguration(name="my-hnsw")
        ]
    )
)

index_client.create_or_update_index(index)