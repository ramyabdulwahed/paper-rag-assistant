from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List
from pathlib import Path #helps when working with files
from capstone.rag.ingest import index_pdf
from capstone.rag.retrieve import retrieve
from capstone.rag.rerank import rank
from capstone.rag.llm import answer_with_context

UPLOAD_DIR = Path("capstone/data/uploads")


app =FastAPI (title="Capstone API") #creates backend app object

class ChatRequest(BaseModel): #baseModel gives class validation powers so it checks the values of the fields when the user sends
   
    #request must include a question and int
    question: str 
    k: int =5

##after the backend answers, what should the response look like?
class ChatResponse (BaseModel): 

    #answer back to user must have an answer and a list of source strings
    answer:str
    sources : List[str]




@app.get("/health") #when someone sends a get request to /health, run below function
def health():
    return {"status": "ok"}


@app.post("/ingest") #when someone sends a post request to /ingest run this function
async def ingest(file: UploadFile = File(...)): #The input is an uploaded file. File(...) = This file is required. The three dots: ... mean required in FastAPI/Pydantic style.
    path = UPLOAD_DIR / file.filename

    with open (path,"wb") as f: #wb cause PDF files are binary files
        f.write(await file.read()) #Waits for the file content to finish reading
    
    #Call our RAG ingestion function
    result = index_pdf (str(path))
    print (result)

    return result

@app.post("/chat", response_model=ChatResponse) #response_model=ChatResponse: this tells FastAPI: the response should match the ChatResponse structure.
def chat (req: ChatRequest): #The function receives a request body shaped like ChatRequest

    intial_hits = retrieve (req.question, k=max(req.k, 10))
    hits = rank (req.question, intial_hits, top_n=req.k)
    #If no chunks are found, return a clear message
    if not hits:
        return ChatResponse (answer="I could not find any relevant chunks. Try uploading and indexing a PDF first.",
            sources=[])

    answer = answer_with_context(req.question, hits)
    sources = [hit["source"] for hit in hits]

    return ChatResponse(answer=answer, sources=sources)
    


