from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import csv
import pandas as pd
import argparse
import time
import torch
import torch.nn.functional as F

def getClient():
    client = AzureOpenAI(
        api_key = os.getenv("EMBEDDING_OPENAI_API_KEY"),
        api_version = os.getenv("EMBEDDING_OPENAI_API_VERSION"),
        azure_endpoint = os.getenv("EMBEDDING_OPENAI_API_ENDPOINT")
    )
    return client

def getEmbedding(client, text, model):
    return client.embeddings.create(input = [text], model=model).data[0].embedding


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add embeddings for contents in csv file")
    parser.add_argument("csv_file", type=str, help="csv file to process")
    parser.add_argument("output_file", type=str, help="output parquet file")
    args = parser.parse_args()
    load_dotenv(override=True)
    embedding_client = getClient()
    embedding_model = os.getenv("EMBEDDING_DEPLOYMENT_NAME")
    result = []
    with open(args.csv_file, mode='r', newline='') as f:
        next(f)
        csv_reader = csv.DictReader(f, fieldnames=["id", "title", "content"])
        for row in csv_reader:
            time.sleep(0.02)
            result.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'normalizedContentVector': F.normalize(torch.tensor(getEmbedding(embedding_client, row['content'], embedding_model)), p=2, dim=0).numpy()
            })
            print("Created embedding for",row['id'])
    df = pd.DataFrame(result)
    print(df)
    df.to_parquet(args.output_file, engine='pyarrow')
    print(f"Converted {args.csv_file} to {args.output_file}")
    