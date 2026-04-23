import os
import chromadb
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
    PromptTemplate
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

Settings.llm = Ollama(model="llama3.1:latest", request_timeout=120.0)
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text") 
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

DB_PATH = "./data/chroma"

QA_PROMPT_TMPL = (
    "La informacion de contexto se encuentra a continuacion.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Dada la informacion de contexto y SIN utilizar conocimiento previo, responde la consulta. "
    "Muestra el paso a paso matematico y formulas en formato LaTeX si aplica.\n"
    "CRITICO: Si la respuesta exacta no esta en el contexto, responde EXACTAMENTE con 'No encontrado'.\n"
    "Consulta: {query_str}\n"
    "Respuesta: "
)

def get_rag_index(data_dir="./data/rag/pdfs"):
    db = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = db.get_or_create_collection("jarvis_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if os.path.exists(data_dir) and os.listdir(data_dir):
        documents = SimpleDirectoryReader(data_dir).load_data()
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, show_progress=True
        )
    else:
        index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )
    return index

def query_rag(query_text: str) -> str:
    try:
        index = get_rag_index()
        query_engine = index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact",
            text_qa_template=PromptTemplate(QA_PROMPT_TMPL)
        )
        response = query_engine.query(query_text)
        return str(response)
    except Exception as e:
        print(f"RAG Error: {e}")
        return "No encontrado"
