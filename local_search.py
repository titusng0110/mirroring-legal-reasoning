import torch
import numpy as np
from dotenv import load_dotenv
import pandas as pd
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagLLMReranker


# Setup embedding model client
load_dotenv(override=True)
embedding_client = SentenceTransformer('BAAI/bge-m3')
reranker = FlagLLMReranker('BAAI/bge-reranker-v2-gemma', use_fp16=True)

# Setup database
databases = None
normalizedContentTensors = None


# Load database
def loadDB(file_paths: Dict) -> bool:
    global databases, normalizedContentTensors
    if databases is None or normalizedContentTensors is None:
        try:
            print("Loading vector databases.")
            databases = {option: pd.read_parquet(file_path,engine="pyarrow") for option, file_path in file_paths.items()}
            normalizedContentTensors = {option: torch.from_numpy(np.stack(df['normalizedContentVector'].to_numpy())).to(torch.float32) for option, df in databases.items()}
            print("Vector databases loaded.")
            return True
        except Exception as e:
            print(f"Error loading database: {e}")
            return False
    else:
        print("Vector databases have already been loaded.")
        return True
        

# search function
def search(database: str, query: str, k: int, bigk: int) -> List[Dict]:
    global databases, normalizedContentTensors
    if databases is None or normalizedContentTensors is None:
        print("Error: Please load database before searching.")
        return [{"error": "Please load database before searching."}]
    else:
        if bigk < k:
            return [{"error": "Initial number of results cannot be less than final number of results."}]
        results = []
        results.append({"query": query, "option": database})
        # Get query from user input and vectorize, then normalize
        queryTensor = torch.tensor(embedding_client.encode([query], normalize_embeddings=True, precision="float32"), dtype=torch.float32)

        # Calculate cosine similarity between the query tensor and all content tensors
        cosine_similarities = torch.matmul(queryTensor, normalizedContentTensors[database].transpose(0,1)).squeeze()

        # Select top bigk results based on cosine similarity
        topk_indices = torch.topk(cosine_similarities, bigk).indices

        # Calculate BM25 rank
        # corpus = databases[database].iloc[topk_indices.numpy()]['content']
        # tokenized_corpus = [nlp.preprocess_text(doc) for doc in corpus]
        # bm25 = BM25Okapi(tokenized_corpus)
        # tokenized_query = nlp.preprocess_text(query)
        # doc_scores = torch.tensor(bm25.get_scores(tokenized_query))

        # Rerank to get topk results
        corpus = databases[database].iloc[topk_indices.numpy()]['content'].to_list()
        batch_size = 2
        doc_scores = []
        for i in range(0, len(corpus), batch_size):
            batch = corpus[i:i+batch_size]
            batch_pairs = [[query, doc] for doc in batch]
            batch_scores = reranker.compute_score(batch_pairs)
            doc_scores.extend(batch_scores)
        # Check if there's a remaining item
        if len(corpus) % 2 != 0:
            last_item = corpus[-1]
            last_pair = [query, last_item]
            last_score = reranker.compute_score(last_pair)
            doc_scores.append(last_score)
        doc_scores = np.array(doc_scores)

        # doc_scores = cosine_similarities[topk_indices].numpy() # control experiment
        topk_similar_items = databases[database].iloc[topk_indices.numpy()].copy()
        topk_similar_items.loc[:, 'reranker_score'] = doc_scores
        topk_similar_items = topk_similar_items.sort_values(by='reranker_score', ascending=False).head(k)

        for i, row in topk_similar_items.iterrows():
            result = {
                "id": row['id'],
                "title": row['title'],
                "cosine_similarity": cosine_similarities[topk_indices[topk_similar_items.index.get_loc(i)]].item(),
                "reranker_score": row['reranker_score'],
                "content": row['content']
            }
            results.append(result)
        return results

def get_content(database:str, specific_id:str) -> str:
    global databases
    if databases is None:
        print("Error: Please load database before searching.")
        return None
    else:
        try:
            content = databases[database].query(f"id == '{specific_id}'")['content'].values[0]
            return content
        except Exception as e:
            return None
        
def get_title(database:str, specific_id:str) -> str:
    global databases
    if databases is None:
        print("Error: Please load database before searching.")
        return None
    else:
        try:
            title = databases[database].query(f"id == '{specific_id}'")['title'].values[0]
            return title
        except Exception as e:
            return None