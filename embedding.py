from uuid import uuid4

import pandas as pd

import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS

from langchain_core.documents import Document

from langchain_huggingface import HuggingFaceEmbeddings


model_name = "deepvk/USER-base"
model_kwargs = {'device': 'mps'}
encode_kwargs = {'normalize_embeddings': True}

embeddings  = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

index = faiss.IndexFlatL2(len(embeddings.embed_query("")))

vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)

chunks = pd.read_csv("./data/chunks.csv").chunks.to_list()

documents = [Document(page_content=chunk) for chunk in chunks]

uuids = [str(uuid4()) for _ in range(len(documents))]

vector_store.add_documents(documents=documents, ids=uuids)

vector_store.save_local("./faiss_index")
