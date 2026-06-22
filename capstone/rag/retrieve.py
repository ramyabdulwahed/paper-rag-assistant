from typing import Dict, List, Any
from capstone.rag.ingest import collection, embed_model


def retrieve (question: str, k: int = 5) -> List [Dict[str, Any]]:
    
    #[0] [0] Because the model returns embeddings for a list of texts. We gave one text, so we get one embedding. Shape idea: Before [0]: [ [0.12, -0.44, 0.08, ...] ] After [0]: [0.12, -0.44, 0.08, ...]
    query_embedding = embed_model.encode([question], normalize_embeddings=True).tolist()[0]

    #Find chunks whose embeddings are closest to this question embedding.
    results = collection.query (query_embeddings=query_embedding, n_results=k,
                                include=["documents", "metadatas", "distances"])
    
    hits = []

    #Extract Chroma results documents = results["documents"][0] metadatas = results["metadatas"][0] distances = results["distances"][0] 
    # This looks weird, but it is important. Chroma supports multiple queries at once. So the result shape is like: results["documents"] = [ [ "chunk 1", "chunk 2", "chunk 3" ] ] The outer list is for query number 1. Because we only asked one question, we use: [0] to get the results for the first query.

    documents = results["documents"][0]
    metadatas = results ["metadatas"][0]
    distances = results ["distances"][0]

    for document, metadata, distance in zip (documents, metadatas, distances):
        source = f"{metadata['source']} — page {metadata['page']}"
        hits.append ({
            "text": document,
            "metadata": metadata,
            "distance" : distance,
            "source": source
        })
    return hits
