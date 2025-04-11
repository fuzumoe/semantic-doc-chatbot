import gc  # noqa: F401
import logging

# Import os and sys for system operations
import os
import sys

# Import traceback for error handling
import traceback
import urllib.parse  # noqa: F401

import awswrangler as wr  # noqa: F401
import boto3  # noqa: F401
import pymongo

# Import FastAPI components for building the web application
from fastapi import FastAPI, HTTPException, UploadFile, status  # noqa: F401

# CORS middleware to handle Cross-Origin Resource Sharing
from fastapi.middleware.cors import CORSMiddleware  # noqa: F401

# Import JSONResponse for returning JSON responses
from fastapi.responses import FileResponse  # noqa: F401
from langchain.callbacks import get_openai_callback  # noqa: F401
from langchain.chains import ConversationalRetrievalChain  # noqa: F401
from langchain.document_loaders import (
    Docx2txtLoader,  # noqa: F401
    PDFMinerLoader,  # noqa: F401
    S3DirectoryLoader,  # noqa: F401
)

# Import langchain for building applications powered by language models
from langchain.text_splitter import RecursiveCharacterTextSplitter  # noqa: F401
from langchain_community.vectorstores import FAISS  # noqa: F401
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: F401
from pydantic import BaseModel  # noqa: F401

LOG = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
S3_URL = os.getenv("S3_ENDPOINT_URL")
S3_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION")
S3_PATH = os.getenv("S3_PATH")
MONGO_URL = os.getenv("MONGO_URL")

for var in [OPENAI_API_KEY, S3_URL, S3_KEY, S3_SECRET, S3_BUCKET, S3_REGION, S3_PATH, MONGO_URL]:
    if var is None:
        LOG.error(f"Environment variable {var} is not set.")
        msg = f"Environment variable {var} is not set."
        raise ValueError(msg)
try:
    client: pymongo.MongoClient = pymongo.MongoClient(MONGO_URL, uuidRepresentation="standard")
    db = client["chat_with_doc"]
    chat_history_collection = db["chat-history"]

    chat_history_collection.create_index([("session_id")], unique=True)
except Exception:
    LOG.exception(traceback.format_exc())
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_tb:
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        LOG.exception(f"{exc_type} {exc_value} {fname} {exc_tb.tb_lineno}")
