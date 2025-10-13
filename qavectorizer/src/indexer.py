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
from os import environ
import json


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
        with open(environ.get('OGG2NAME_INDEX'), 'r') as fd:
            self.ogg2name_index = json.load(fd)

    def create_index(self, name: str):
        return create_elastic_index(name)

    def ogg2name(self, ogg):
        found = self.ogg2name_index.get(str(ogg))
        if found:
            return '{}/{}'.format(found['desc_materia'], found['desc_oggetto'])
        else:
            print('UNKNWOWN Metadata for codice oggetto', str(ogg))
            return 'Codice Oggetto {}'.format(ogg)

    def tipodoc2name(self, tipo):
        # TODO
        if tipo == "S":
            return "Sentenza"
        else:
            return tipo


    def index(self, index: str, doc: dict):
        METADATA_MAP = {
            'annosentenza': lambda x: {'type': 'Anno Sentenza', 'value': x, "display_name": str(x)},
            'annoruolo': lambda x: {'type': 'Anno Ruolo', 'value': x, "display_name": str(x)},
            'codiceoggetto': lambda x: {'type': 'Codice Oggetto', 'value': self.ogg2name(x), "display_name": str(self.ogg2name(x))},
            # 'parte': lambda x: {'type': 'Parte', 'value': x, "display_name": str(anonymize(x))},
            # 'controparte': lambda x: {'type': 'Controparte', 'value': x, "display_name": str(anonymize(x))},
            'nomegiudice': lambda x: {'type': 'Nome Giudice', 'value': x, "display_name": str(x)},
            'tipodocumento': lambda x: {'type': 'Tipo Documento', 'value': self.tipodoc2name(x), "display_name": str(self.tipodoc2name(x))},
            }

        annotations = [
            {
                "id": cluster["id"],
                # this will be a real ER id when it exists
                "id_ER": cluster["url"],
                "start": 0,
                "end": 0,
                "type": cluster["type"],
                "mention": cluster["title"],
                "is_linked": cluster.get('url') and 'wikipedia.org' in cluster['url'],
                # this is temporary, there will be a display name directly in the annotaion object
                "display_name": anonymize(cluster["title"]) if cluster['type'] in self.anonymize_type else cluster['title'],
                "anonymize": cluster['type'] in self.anonymize_type,
            } for cluster in doc['features']['clusters']['entities_consolidated'] #\
                # if cluster["type"] not in ['parte', 'controparte']
        ]

        metadata = [METADATA_MAP[mk](mv) for mk, mv in doc['features'].items() if mk in METADATA_MAP]

        elastic_doc = {
            "mongo_id": doc["id"],
            "name": doc["name"],
            "text": doc["text"],
            "metadata": metadata,
            "annotations": annotations,
        }

        return index_elastic_document(index, elastic_doc)
