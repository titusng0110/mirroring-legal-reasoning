import pandas as pd
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os
import argparse

if __name__ == "__main__":
    #parse arg
    parser = argparse.ArgumentParser(description="Read parquet file and upload to azure")
    parser.add_argument("parquet_file", type=str, help="the parquet file")
    args = parser.parse_args()

    # setup
    load_dotenv(override=True)
    service_endpoint = f"{os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')}"
    index_creds = AzureKeyCredential(os.getenv("AZURE_SEARCH_INDEX_KEY"))
    text_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    text_search_client = SearchClient(endpoint=service_endpoint, index_name=text_search_index_name, credential=index_creds)

    #upload
    df = pd.read_parquet(args.parquet_file, engine="pyarrow")
    df = df[['id', 'title', 'content', 'contentVector']] # dont use titleVector
    rows_as_dicts = df.to_dict(orient='records')
    print(f"total number of chunks = {len(rows_as_dicts)}")
    next_upload = 0
    for i in range(len(rows_as_dicts)):
        # rows_as_dicts[i]['titleVector'] = rows_as_dicts[i]['titleVector'].tolist()
        rows_as_dicts[i]['contentVector'] = rows_as_dicts[i]['contentVector'].tolist()
        if i % 500 == 499 or i == len(rows_as_dicts) - 1:
            text_search_client.upload_documents(documents=rows_as_dicts[next_upload : i + 1])
            print(f"chunks {next_upload} to {i} uploaded")
            next_upload = i + 1

