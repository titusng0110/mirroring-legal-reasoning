import torch
import torch.nn.functional as F
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv
import pandas as pd
import os
from rank_bm25 import BM25Okapi
from typing import List, Dict
import nlp


# Setup embedding model client
load_dotenv(override=True)
embedding_client = AzureOpenAI(
    api_key=os.getenv("EMBEDDING_OPENAI_API_KEY"),
    api_version=os.getenv("EMBEDDING_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("EMBEDDING_OPENAI_API_ENDPOINT")
)
embedding_model = os.getenv("EMBEDDING_DEPLOYMENT_NAME")


# Setup database
databases = None
normalizedContentTensors = None


# Load database
def loadDB(file_paths: Dict) -> bool:
    global databases, normalizedContentTensors
    if databases is None or normalizedContentTensors is None:
        try:
            print("Loading vector databases.\n")
            databases = {option: pd.read_parquet(file_path,engine="pyarrow") for option, file_path in file_paths.items()}
            normalizedContentTensors = {option: torch.from_numpy(np.stack(df['normalizedContentVector'].to_numpy())).to(torch.float32) for option, df in databases.items()}
            print("Vector databases loaded.\n")
            return True
        except Exception as e:
            print(f"Error loading database: {e}\n")
            return False
    else:
        print("Vector databases have already been loaded.\n")
        return True
        


# search function
def search(database: str, query: str, k: int, threshold: float) -> List[Dict]:
    global databases, normalizedContentTensors
    if databases is None or normalizedContentTensors is None:
        print("Error: Please load database before searching.\n")
        return [{"error": "Please load database before searching."}]
    else:
        results = []
        results.append({"query": query})
        # Get query from user input and vectorize, then normalize
        queryVector = embedding_client.embeddings.create(input=[query], model=embedding_model).data[0].embedding
        queryTensor = F.normalize(torch.tensor(queryVector), p=2, dim=0).to(torch.float32)

        # Calculate cosine similarity between the query tensor and all content tensors
        cosine_similarities = torch.matmul(queryTensor, normalizedContentTensors[database].transpose(0, 1))

        # Filter results with cosine similarity >= threshold
        threshold_indices = torch.nonzero(cosine_similarities >= threshold).squeeze()

        # Check if there are no results or fewer than k results
        if threshold_indices.numel() == 0:
            results.append([{"warning": f"No results found with cosine similarity greater than or equal to {threshold}."}])
            return results
        elif len(threshold_indices) < k:
            results.append({"warning": f"Only {len(threshold_indices)} results found with cosine similarity greater than or equal to {threshold}."})

        # Select top k results based on cosine similarity
        if len(threshold_indices) > 0:
            topk_indices = threshold_indices[torch.topk(cosine_similarities[threshold_indices], min(k, len(threshold_indices))).indices]
            
            # Calculate BM25 rank
            corpus = databases[database].iloc[topk_indices.numpy()]['content']
            tokenized_corpus = [nlp.preprocess_text(doc) for doc in corpus]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = nlp.preprocess_text(query)
            doc_scores = torch.tensor(bm25.get_scores(tokenized_query))

            # Retrieve results sorted by BM25 scores
            topk_similar_items = databases[database].iloc[topk_indices.numpy()].copy()
            topk_similar_items.loc[:, 'bm25_score'] = doc_scores.numpy()
            topk_similar_items = topk_similar_items.sort_values(by='bm25_score', ascending=False).head(k)

            for i, row in topk_similar_items.iterrows():
                result = {
                    "title": row['title'],
                    "cosine_similarity": cosine_similarities[topk_indices[topk_similar_items.index.get_loc(i)]].item(),
                    "bm25_score": row['bm25_score'],
                    "content": row['content']
                }
                results.append(result)
        return results