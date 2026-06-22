from typing import Dict, List,Any
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"



# purpose: This function takes reranked chunks and turns them into one context string
# Input: list of retrieved chunks
# Output: formatted context for the LLM
def build_context (hits: List[Dict[str, Any]]) -> str:
    context_parts = []
    for i,hit in enumerate (hits, start=1):
        #This creates one context block. Example: [1] Source: L05_API_Contracts.pdf — page 11 The Power of static Goal: Hide the mess...
        context_parts.append(
            f"[{i}] Source: {hit['source']}\n"
            f"Text: {hit['text']}"
        )
    return "\n\n --- \n\n".join (context_parts)


#purpose:This builds the full instruction sent to the LLM
def build_prompt (question: str, hits: List[Dict[str,Any]]) ->str:
    context = build_context(hits) #First, turn the chunks into context
    return f"""
You are a careful document question-answering assistant.

Use ONLY the context below to answer the question.
If the answer is not in the context, say:
"I don't know based on the provided document."

Cite sources using bracket numbers like [1], [2], etc.

Context:
{context}

Question:
{question}

Answer:
""".strip()

#This sends the prompt to Ollama and returns the model answer.
def call_ollama (prompt:str) -> str:

    payload = {
        "model": MODEL_NAME,
        "messages": [
        {"role": "system", "content": "You answer questions using only the provided document context."},
        {"role": "user", "content": prompt }
        ],
        "stream" : False, #wait for the full answer, then return it
        "options": {
            "temperature": 0.2 #make answer less random
        }
    }
    response = requests.post (OLLAMA_URL, json=payload,timeout=120)
    response.raise_for_status() #If Ollama returns an error, Python raises an exception

    #Ollama returns something like this: { "model": "llama3.2:3b", "created_at": "...", "message": { "role": "assistant", "content": "The power of static is that it hides implementation details..." }, "done": True }
    data = response.json()
    return data["message"]["content"]


#the below function calls the above 2:
def answer_with_context(question: str, hits: List[Dict[str, Any]]) -> str:
    prompt = build_prompt(question, hits)
    return call_ollama(prompt)