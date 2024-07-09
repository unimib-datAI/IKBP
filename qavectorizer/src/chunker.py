from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

class DocumentChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int, length_function=len):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
        )

    def chunk(self, text: str):
        return [
            doc.page_content
            for doc in self.text_splitter.create_documents(texts=[text])
        ]


class Embedder:
    _model_name = "distiluse-base-multilingual-cased-v1"
    _tokenizer = None
    _model = None

    def __init__(self):
        self.embeddings = None
        self._model = SentenceTransformer(self._model_name).to("cuda")

    def embed(self, text):

        embedding_list = self._model.encode(text)
        self.embeddings = embedding_list
        return embedding_list
