import gc
import logging
from typing import Any

from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.callbacks.manager import get_openai_callback
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings  # ✅ New location
from langchain_openai import ChatOpenAI

from app.backend.accessors import get_collection, get_s3_client
from app.backend.config import get_config_variables
from app.backend.utils import get_temp_file_path, load_memory_to_pass

LOG = logging.getLogger(__name__)
CONFIG = get_config_variables()

CHAT_HISTORY_COLLECTION = get_collection()
S3_CLIENT = get_s3_client()


def get_response(
    file_name: str,
    session_id: str,
    query: str,
    model: str = "mistralai/Mistral-7B-Instruct-v0.1",
    temperature: float = 0.0,
) -> Any:
    """Get the response from the model."""
    LOG.info(f"file name is {file_name}")

    # Prepare file path
    file_name = file_name.split("/")[-1]
    temp_file = get_temp_file_path(file_name)
    local_file = str(temp_file.absolute())
    object_key = f"{CONFIG.S3_PATH}/{file_name}"

    # Download file from S3
    S3_CLIENT.download_file(CONFIG.S3_BUCKET, object_key, local_file)

    # Load document
    loader = Docx2txtLoader(file_path=local_file) if file_name.endswith(".docx") else PyPDFLoader(file_name)
    data = loader.load()

    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0, separators=["\n", " ", ""])
    all_splits = text_splitter.split_documents(data)

    # ✅ Use open-source embedding model (FREE + no API needed)
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-small-v2")

    # Build FAISS vectorstore
    vectorstore = FAISS.from_documents(all_splits, embeddings)

    # Use Together-compatible ChatOpenAI model
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
    )

    # Create retrieval QA chain
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 1}),
    )

    # Generate answer
    with get_openai_callback() as cb:
        answer = qa_chain(
            {
                "question": query,
                "chat_history": load_memory_to_pass(session_id=session_id),
            }
        )
        LOG.info(f"Total Tokens: {cb.total_tokens}")
        LOG.info(f"Prompt Tokens: {cb.prompt_tokens}")
        LOG.info(f"Completion Tokens: {cb.completion_tokens}")
        LOG.info(f"Total Cost (in $): {cb.total_cost}")

        answer["total_tokens_used"] = cb.total_tokens

    gc.collect()
    return answer
