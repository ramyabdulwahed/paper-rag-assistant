from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
import chromadb
from sentence_transformers import SentenceTransformer
import re

CHROMA_DIR = "capstone/chroma_store"
COLLECTION_NAME = "askaboutpaper"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNKING_MODE = "token"

client = chromadb.PersistentClient (path=CHROMA_DIR) #create a persistant(ex. saved to disk) chromadb client
collection = client.get_or_create_collection (COLLECTION_NAME) #create/use collection
embed_model = SentenceTransformer (EMBED_MODEL_NAME) #load embed model to memory to convert text to vectors


#deletes old chunks before indexing a new pdf
def clear_collection() -> int:
    existing = collection.get() ##Give me the records currently stored in this collection. The result is a dictionary.
    ids = existing.get("ids", []) #extract the ids array if not there return []
    if ids:
        collection.delete(ids=ids) #delet all chunks with these ids 
    return len(ids) #return # of deleted chunks





# Purpose - This function takes a PDF path and returns a list of pages.

# Example output:
# [
#     {"page": 1, "text": "Abstract..."},
#     {"page": 2, "text": "Introduction..."},
#     {"page": 3, "text": "Methods..."}
# ]

# Why page-by-page? Because later citations can say: Source: contract.pdf, page 2
def extract_text (pdf_path: str) -> List[Dict[str, Any]]:

    reader = PdfReader (pdf_path) #reader represents pdf file

    pages = []
    for page_number, page in enumerate (reader.pages, start=1):
        
        text = page.extract_text()
        if not text:
            text = ""
        if text.strip(): #check if page is real and remove white spaces
            pages.append ({"page": page_number, "text": text})
    return pages

#this runs after the above function and turns text into smaller chunks
def chunk_text (text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    
    #for each page break it further in paragraphs by looking for double new lines

    paras = re.split (r"\n{2,}", text)
    chunks, buffer = [], ""

    for p in paras:
        if len(buffer) + len(p) < chunk_size:
            #if buffer contains text we add two new lines and then the new paragaph else only the new paragaph
            buffer = (buffer + "\n\n" + p) if buffer else p
        else: #if space is not enough
            #save old paragaph
            chunks.append (buffer)
            #carry one last 200 chars from last paragraph for overlap and add new one
            buffer = buffer[-overlap: ] + "\n\n" + p
    if buffer:
        chunks.append (buffer)
    
    cleaned_chunks = []
    for c in chunks:
        cleaned = c.strip()
        if cleaned:
            cleaned_chunks.append (cleaned)
    
    return cleaned_chunks



def get_embedding_tokenizer():
    if hasattr (embed_model, "tokenizer"):
        return embed_model.tokenizer
    return embed_model._first_module().tokenizer

def chunk_text_by_tokens(text: str, max_tokens: int = 200, overlap_tokens: int = 40) -> List[str]:
    tokenizer = get_embedding_tokenizer()
    token_ids = tokenizer.encode (text, add_special_tokens=False) #This converts text into token IDs.Tokens are not always words. A long word may become multiple tokens.

    chunks = []
    start = 0

    while start < len(token_ids):
        end = start + max_tokens #ex. 0 -200
        chunk_ids = token_ids[start:end]

        achunk_text = tokenizer.decode (chunk_ids, skip_special_tokens=True).strip()

        if achunk_text:
            chunks.append (achunk_text)
        if end >= len (token_ids):
            break
        start += max_tokens - overlap_tokens #next token will start at 160 for overlap
    return chunks





def index_pdf (pdf_path: str) -> Dict[str, Any]:
    pdf_path_obj = Path (pdf_path) #PDF path into a Path object. This lets us use: pdf_path_obj.name pdf_path_obj.stem Example: pdf_path = capstone/data/uploads/contract.pdf pdf_path_obj.name = contract.pdf pdf_path_obj.stem = contract
    deleted_old_chunks = clear_collection() #delete old pdf before adding new one
    pdf_total_pages = len(PdfReader(pdf_path).pages) #count how many pages
    pages = extract_text (pdf_path) #pages is going to be a list of dicts ex. list of pages
    
    documents, metadata, ids = [], [], []
    for p in pages:
        page_number = p["page"]
        page_text = p["text"]

        #call chunking function to break page further into chunks
        #page_chunks = chunk_text(page_text) # page_chunks will be list of strings

        if CHUNKING_MODE == "token":
            page_chunks = chunk_text_by_tokens(
                page_text,
                max_tokens=200,
                overlap_tokens=40
            )
        else:
            page_chunks = chunk_text(page_text)

        for chunk_number, chunk in enumerate (page_chunks):
            
            #for each chunk we create its needed metadata for chroma
            doc_id = f"{pdf_path_obj.stem}-p{page_number}-c{chunk_number}"
            
            documents.append(chunk)
            metadata.append({
                "source": pdf_path_obj.name,
                "page": page_number,
                "chunk" :chunk_number
            })

            ids.append(doc_id)
    if not documents: #handle empty pdfs
        return {
        "source": pdf_path_obj.name,
        "pdf_total_pages": pdf_total_pages,
        "pages": len(pages),
        "chunks": 0,
        "deleted_old_chunks": deleted_old_chunks,
        "status": "no text found"}
    
    #This deletes old chunks for the same PDF before re-indexing. i commented it since we already call clear collection in index function
    #collection.delete(where= {"source" : pdf_path_obj.name})

    embeddings = embed_model.encode(documents, normalize_embeddings=True).tolist() #.tolist() converts nympy array to python for chroma
    #upsert = update if it exists, add if new
    collection.upsert (ids=ids,
                        documents=documents,
                        metadatas=metadata,
                        embeddings=embeddings
                        )
    return {
        "source": pdf_path_obj.name,
        "pdf_total_pages": pdf_total_pages,
        "pages" : len(pages),
        "chunks" : len(documents),
        "deleted_old_chunks": deleted_old_chunks,
        "status": "indexed"
    }


