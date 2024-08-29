from pydantic_settings import BaseSettings
import os


class AppSettings(BaseSettings):
    # titan host base url
    host_base_url: str = os.getenv("HOST_BASE_URL", "10.0.2.29")
    # port where the indexer runs
    indexer_server_port: str = os.getenv("INDEXER_SERVER_PORT", "7863")
    # port where the documents service runs
    docs_port: str = os.getenv("DOCS_PORT", "50080")
    # port where chromadb runs
    chroma_port: str = os.getenv("CHROMA_PORT", "8000")
    # port where elastic runs
    elastic_port: str = os.getenv("ELASTIC_PORT", "9201")
    # the mebedding models used, if you change the model you also have the re-index documents
    embedding_model: str = os.getenv(
        "SENTENCE_TRANSFORMER_EMBEDDING_MODEL",
        # "efederici/sentence-BERTino-v2-pt",
        "efederici/sentence-IT5-base",
        # "nickprock/mmarco-bert-base-italian-uncased",
    )
    chunk_size: int = 200
    chunk_overlap: int = 20
    # elastic serach index name and chromadb collection name
    index_collection_name: str = "test"
