import streamlit as st
import requests

st.set_page_config(page_title="Ask the paper", layout="wide") # #browser title
st.title ("Ask the papers")

API = "http://localhost:8000"

#Put the following UI elements inside the sidebar to the left
with st.sidebar:

    st.header("ingest") #creates a sidebar called ingest label
    up =st.file_uploader ("UPLOAD PDF", type=["pdf"]) #stores the uploaded file object

    if up and st.button ("index"): #If a file has been uploaded AND the user clicks the Index button, then run the upload code
        r = requests.post (f"{API}/ingest", files = {"file": (up.name, up.getvalue(), "application/pdf")}) #sends the PDF to the backend. up.getvalue() Gets the actual bytes of the uploaded PDF

        if r.ok:
            st.session_state.history = [] #when we upload new pdfs old messages should disappear
            st.success (r.json())

        else:
            st.error (f" failed: {r.text}")

if "history" not in st.session_state: #Sreamlit reruns your script from top to bottom every time the user interacts with it. That means without memory, chat messages would disappear. st.session_state stores data between reruns.
    st.session_state.history = []

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"]) #Displays the message content. Markdown means it can render: bold text lists code links

#This line: if q := st.chat_input("Ask about the document..."): is similar to: q = st.chat_input("Ask about the document...") if q: So if the user types a question, it gets stored in q.
if q := st.chat_input("Ask about the document..."): #Shows an input box at the bottom of the app. The placeholder text is: Ask about the document...
    st.session_state.history.append({"role": "user", "content": q})

    with st.chat_message("user"):
        st.markdown(q) #show user message immediately

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."): #hows a loading spinner while the backend is working
            #send request to backend. This matches our backend model: class ChatRequest(BaseModel): question: str k: int = 5
            r = requests.post(
                f"{API}/chat",
                json={"question": q, "k": 5}
            )

            if r.ok:
                data = r.json()
                answer = data["answer"]
                sources = data["sources"]
            else:
                answer = f"Request failed: {r.text}"
                sources = []

        st.markdown(answer) #Displays the assistant answer.

        with st.expander("Sources"): #Creates a collapsible section called Sources
            if sources:
                for s in sources:
                    st.caption(s) #show sources
            else:
                st.caption("No sources yet.")
    #This stores the assistant answer in chat history. Now the conversation has both: {"role": "user", "content": q} {"role": "assistant", "content": answer}
    st.session_state.history.append({"role": "assistant", "content": answer}) 



