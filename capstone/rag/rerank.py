from typing import Dict, List, Any
from sentence_transformers import CrossEncoder

RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

rerank_model = CrossEncoder (RERANK_MODEL_NAME)

def rank(question: str, hits: List[Dict[str,Any]], top_n: int=3) -> List[Dict[str, Any]]: #hits = retrieved chunks from Chroma

    if not hits:
        return []
    #The cross-encoder expects pairs
    #Example: [ ("what is my coverage?", "Auto insurance policy..."), ("what is my coverage?", "Collision coverage applies...")]
    pairs = [(question, hit["text"]) for hit in hits]

    #The model gives a relevance score for each pair. higher score = higher relevance
    scores = rerank_model.predict (pairs)

    for hit, score in zip(hits, scores):
        hit["rerank_score"] = float (score)
    
    #This sorts hits from highest relevance score to lowest.key=lambda hit: hit["rerank_score"] This tells Python: Sort using the rerank_score field.
    #reverse=True This means: highest score first
    reranked_hits = sorted (hits, key=lambda hit: hit["rerank_score"], reverse=True)

    return reranked_hits[:top_n]
    
