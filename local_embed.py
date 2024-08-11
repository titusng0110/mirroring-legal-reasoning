from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import csv
import pandas as pd
import argparse

def getClient():
    model = SentenceTransformer('BAAI/bge-m3')
    return model

def getEmbeddings(client, texts):
    return client.encode(texts, normalize_embeddings=True, precision="float32")

def process_batch(batch, embedding_client):
    texts = [row['content'] for row in batch]
    embeddings = getEmbeddings(embedding_client, texts)
    
    result = []
    for row, embedding in zip(batch, embeddings):
        result.append({
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'normalizedContentVector': embedding
        })
        print(f"Created embedding for {row['id']}")
    
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add embeddings for contents in csv file")
    parser.add_argument("csv_file", type=str, help="csv file to process")
    parser.add_argument("output_file", type=str, help="output parquet file")
    args = parser.parse_args()
    
    load_dotenv(override=True)
    embedding_client = getClient()
    csv.field_size_limit(500*1024*1024)
    
    result = []
    batch = []
    batch_size = 46
    
    with open(args.csv_file, mode='r', newline='') as f:
        next(f)
        csv_reader = csv.DictReader(f, fieldnames=["id", "title", "content"])
        
        for row in csv_reader:
            batch.append(row)
            
            if len(batch) == batch_size:
                result.extend(process_batch(batch, embedding_client))
                batch = []
        
        # Process any remaining items
        if batch:
            result.extend(process_batch(batch, embedding_client))
    
    df = pd.DataFrame(result)
    print(df)
    df.to_parquet(args.output_file, engine='pyarrow')
    print(f"Converted {args.csv_file} to {args.output_file}")