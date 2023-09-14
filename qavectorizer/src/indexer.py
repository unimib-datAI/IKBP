from sentence_transformers import SentenceTransformer
from chunker import DocumentChunker
from actions import (
    index_chroma_document,
    create_chroma_collection,
    index_elastic_document,
    create_elastic_index,
)
from utils import anonymize
import torch


class ChromaIndexer:
    def __init__(self, embedding_model: str, chunk_size: int, chunk_overlap: int):
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_model.to("cuda")
        self.embedding_model.eval()

        self.chunker = DocumentChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def __embed(self, text: str):
        chunks = self.chunker.chunk(text)
        embeddings = []
        with torch.no_grad():
            embeddings = self.embedding_model.encode(chunks)

        embeddings = embeddings.tolist()
        return chunks, embeddings

    def create_index(self, name: str):
        return create_chroma_collection(name)

    def index(self, collection: str, doc: dict, metadata):
        chunks, embeddings = self.__embed(doc["text"])

        metadatas = [metadata for _ in chunks]

        res = index_chroma_document(
            collection,
            {
                "documents": chunks,
                "embeddings": embeddings,
                "metadatas": metadatas,
            },
        )
        del embeddings
        del chunks

        return res


class ElasticsearchIndexer:
    def __init__(self, anonymize_type=[]):
        self.anonymize_type = anonymize_type

    def create_index(self, name: str):
        return create_elastic_index(name)

    def index(self, index: str, doc: dict):
        annotations = [
            {
                "id": ann["_id"],
                # this will be a real ER id when it exists
                "id_ER": ann["_id"],
                "start": ann["start"],
                "end": ann["end"],
                "type": ann["type"],
                "mention": ann["features"]["mention"],
                "is_linked": ann["features"]["url"] != None
                and (not ann["features"]["linking"]["is_nil"]),
                # this is temporary, there will be a display name directly in the annotaion object
                "display_name": anonymize(ann["features"]["mention"])
                if ann["type"] in self.anonymize_type
                else ann["features"]["mention"],
            }
            for ann in doc["annotation_sets"]["entities_merged"]["annotations"]
        ]

        metadata = [
            # for now let's make them static
            {"type": "anno sentenza", "value": doc["features"].get("annosentenza", "")},
            {"type": "anno ruolo", "value": doc["features"].get("annoruolo", "")},
        ]

        elastic_doc = {
            "mongo_id": doc["id"],
            "name": doc["name"],
            "text": doc["text"],
            "metadata": metadata,
            "annotations": annotations,
        }

        return index_elastic_document(index, elastic_doc)
