from elasticsearch import Elasticsearch
import uvicorn
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends
import chromadb
from chromadb import errors
from chromadb.config import Settings
import uuid
from sentence_transformers import SentenceTransformer
from functools import lru_cache
from settings import AppSettings
from retriever import DocumentRetriever
from utils import (
    get_facets_annotations,
    get_facets_metadata,
    get_hits,
    get_facets_annotations_no_agg,
)
import torch
from os import environ
import json
import os
import logging
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.DEBUG)


@lru_cache()
def get_settings():
    return AppSettings()


# Setup FastAPI:
app = FastAPI()

# I need open CORS for my setup, you may not!!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/chroma/collection/{collection_name}")
def get_collection(collection_name):
    try:
        return chroma_client.get_collection(name=collection_name)
    except Exception:
        raise HTTPException(status_code=404049, detail="Collection not found")


class CreateCollectionRequest(BaseModel):
    name: str


@app.post("/chroma/collection")
def create_collection(req: CreateCollectionRequest):
    # try:
    collection = chroma_client.get_or_create_collection(name=req.name)
    count = collection.count()

    return {**collection.dict(), "n_documents": count}
    # except Exception:
    #     raise HTTPException(status_code=409, detail="Collection already exists")


@app.get("/chroma/collection/{collection_name}/count")
def count_collection_docs(collection_name):
    try:
        collection = chroma_client.get_collection(collection_name)
        count = collection.count()

        return {"total_docs": count}

    except Exception:
        raise HTTPException(
            status_code=500, detail="Something went wrong when counting documents"
        )


@app.delete("/chroma/collection/{collection_name}")
def delete_collection(collection_name):
    try:
        chroma_client.delete_collection(name=collection_name)
        return {"count": 1}
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Collection not found")


class IndexDocumentRequest(BaseModel):
    embeddings: List[List[float]]
    documents: List[str]
    metadatas: List[dict] = []


@app.post("/chroma/collection/{collection_name}/doc")
def index_chroma_document(req: IndexDocumentRequest, collection_name):
    try:
        collection = chroma_client.get_collection(collection_name)
        chunks_ids = [str(uuid.uuid4()) for _ in req.embeddings]

        collection.add(
            documents=req.documents,
            embeddings=req.embeddings,
            metadatas=req.metadatas,
            ids=chunks_ids,
        )

        return {"added": len(req.embeddings)}
    except errors.IDAlreadyExistsError:
        raise HTTPException(
            status_code=409, detail="A document with the same id already exists"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=req.embeddings)


@app.delete("/chroma/collection/{collection_name}/doc/{document_id}")
def delete_document(collection_name, document_id):
    try:
        # delete indexed embeddings for the document
        collection = chroma_client.get_collection(collection_name)
        collection.delete(where={"doc_id": document_id})
        return {"count": 1}

    except Exception:
        raise HTTPException(
            status_code=500, detail="Something went wrong when deleting the document"
        )


class QueryCollectionRquest(BaseModel):
    query: str
    k: int = 5
    where: dict = None
    include: List[str] = ["metadatas", "documents", "distances"]


class CustomJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


@app.post(
    "/chroma/collection/{collection_name}/query", response_class=CustomJSONResponse
)
async def query_collection(collection_name: str, req: QueryCollectionRquest):
    # try:
    # get most similar chunks
    # collection = chroma_client.get_collection(collection_name)
    embeddings = []

    with torch.no_grad():
        # create embeddings for the query
        embeddings = model.encode(req.query)
    embeddings = embeddings.tolist()
    print(len(embeddings))
    query_body = {
        "knn": {
            "inner_hits": {
                "_source": False,
                "fields": ["chunks.vectors.text", "_score"],
            },
            "field": "chunks.vectors.predicted_value",  # Replace with your vector field name
            "query_vector": embeddings,
            "k": 5,  # Number of nearest neighbors to return (adjust as needed)
        },
    }
    results = es_client.search(index=collection_name, body=query_body)

    del embeddings

    doc_chunk_ids_map = {}
    for hit in results["hits"]["hits"]:
        doc_id = hit["_source"]["id"]
        for chunk in hit["inner_hits"]["chunks.vectors"]["hits"]["hits"]:
            chunk_text = chunk["fields"]["chunks"][0]["vectors"][0]["text"][0]
            chunk = {
                "id": doc_id,
                "distance": hit["_score"],
                "text": chunk_text,
                "metadata": {"doc_id": doc_id, "chunk_size": len(chunk_text)},
            }

        if doc_id in doc_chunk_ids_map:
            doc_chunk_ids_map[doc_id].append(chunk)
        else:
            doc_chunk_ids_map[doc_id] = [chunk]
    full_docs = []

    # get full documents from db
    doc_ids = list(doc_chunk_ids_map.keys())

    for doc_id in doc_ids:
        d = retriever.retrieve(doc_id)
        # d = requests.get(
        #     "http://"
        #     + settings.host_base_url
        #     + ":"
        #     + settings.docs_port
        #     + "/api/mongo/document/"
        #     + str(doc_id)
        # ).json()
        full_docs.append(d)

    doc_results = []

    for doc in full_docs:
        doc_results.append({"doc": doc, "chunks": doc_chunk_ids_map[doc["id"]]})

    return doc_results


class CreateElasticIndexRequest(BaseModel):
    name: str


@app.post("/elastic/index")
def create_elastic_index(req: CreateElasticIndexRequest):
    if es_client.indices.exists(index=req.name):
        index = es_client.indices.get(index=req.name)
        count = es_client.count(index=req.name)

        return {**index, "n_documents": count}

    # try:
    es_client.indices.create(
        index=req.name,
        mappings={
            "properties": {
                "metadata": {
                    "type": "nested",
                    "properties": {
                        "type": {"type": "keyword"},
                        "value": {"type": "keyword"},
                    },
                },
                "annotations": {
                    "type": "nested",
                    "properties": {
                        "id_ER": {"type": "keyword"},
                        "type": {"type": "keyword"},
                    },
                },
            }
        },
    )

    index = es_client.indices.get(index=req.name)

    return {**index, "n_documents": 0}


@app.delete("/elastic/index/{index_name}")
def delete_elastic_index(index_name):
    try:
        es_client.indices.delete(index=index_name)
        return {"count": 1}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error while deleting index")


class IndexElasticDocumentRequest(BaseModel):
    doc: dict


def index_elastic_document_raw(doc, index_name):
    res = es_client.index(index=index_name, document=doc)
    es_client.indices.refresh(index=index_name)
    return res["result"]


@app.post("/elastic/index/{index_name}/doc")
def index_elastic_document(req: IndexElasticDocumentRequest, index_name):
    return index_elastic_document_raw(req.doc, index_name)
    # try:
    #     collection = chroma_client.get_collection(collection_name)
    #     chunks_ids = [str(uuid.uuid4()) for _ in req.embeddings]

    #     collection.add(
    #         documents=req.documents,
    #         embeddings=req.embeddings,
    #         metadatas=req.metadatas,
    #         ids=chunks_ids,
    #     )

    #     return {"added": len(req.embeddings)}
    # except errors.IDAlreadyExistsError:
    #     raise HTTPException(
    #         status_code=409, detail="A document with the same id already exists"
    #     )
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=req.embeddings)


def ogg2name(ogg):
    return ogg2name_index.get(ogg, "UNKNOWN")


def tipodoc2name(tipo):
    # TODO
    if tipo == "S":
        return "Sentenza"
    else:
        return tipo


def anonymize(s, s_type="persona", anonymize_type=["persona"]):
    if s_type in anonymize_type:
        words = s.split()
        new_words = ["".join([word[0]] + ["*" * (len(word) - 1)]) for word in words]
        return " ".join(new_words)
    else:
        return s


@app.post("/elastic/index/{index_name}/doc/mongo")
def index_elastic_document_mongo(req: IndexElasticDocumentRequest, index_name):
    METADATA_MAP = {
        "annosentenza": "Anno Sentenza",
        "annoruolo": "Anno Rouolo",
        "codiceoggetto": lambda x: ogg2name(x),
        "parte": "Parte",
        "controparte": "Controparte",
        "nomegiudice": "Nome Giudice",
        "tipodocumento": lambda x: tipodoc2name(x),
    }

    mongo_doc = req.doc

    doc = {}
    doc["mongo_id"] = mongo_doc["id"]
    doc["name"] = mongo_doc["name"]
    doc["text"] = mongo_doc["text"]
    doc["metadata"] = [
        {"type": mk, "value": mv}
        for mk, mv in mongo_doc["features"].items()
        if mk in METADATA_MAP
    ]

    doc["annotations"] = [
        {
            "id": cluster["id"],
            # this will be a real ER id when it exists
            "id_ER": cluster["id"],
            "start": 0,
            "end": 0,
            "type": cluster["type"],
            "mention": cluster["title"],
            "is_linked": bool(cluster.get("url", False)),
            # this is temporary, there will be a display name directly in the annotaion object
            "display_name": anonymize(cluster["type"], cluster["title"]),
        }
        for cluster in mongo_doc["features"]["clusters"]["entities_merged"]
    ]

    return index_elastic_document_raw(doc, index_name)


class QueryElasticIndexRequest(BaseModel):
    text: str
    metadata: list = None
    annotations: list = None
    n_facets: int = 20
    page: int = 1
    documents_per_page: int = 20


@app.post("/elastic/index/{index_name}/query")
async def query_elastic_index(
    index_name: str,
    req: QueryElasticIndexRequest,
):
    print("received request", req.dict())
    from_offset = (req.page - 1) * req.documents_per_page

    # build a query that retrieve conditions based AND conditions between text, annotation facets and metadata facets
    query = {
        "bool": {
            "must": [{"query_string": {"query": req.text, "default_field": "text"}}]
        },
    }

    if req.annotations != None and len(req.annotations) > 0:
        for annotation in req.annotations:
            query["bool"]["must"].append(
                {
                    "nested": {
                        "path": "annotations",
                        "query": {
                            "bool": {
                                "filter": [
                                    {
                                        "term": {
                                            "annotations.id_ER": annotation["value"]
                                        }
                                    },
                                    {"term": {"annotations.type": annotation["type"]}},
                                ]
                            }
                        },
                    }
                },
            )

    if req.metadata != None and len(req.metadata) > 0:
        for metadata in req.metadata:
            query["bool"]["must"].append(
                {
                    "nested": {
                        "path": "metadata",
                        "query": {
                            "bool": {
                                "filter": [
                                    {"term": {"metadata.value": metadata["value"]}},
                                    {"term": {"metadata.type": metadata["type"]}},
                                ]
                            }
                        },
                    }
                },
            )

    search_res = es_client.search(
        index=index_name,
        size=20,
        # source_excludes=["text"],
        from_=from_offset,
        query=query,
        # aggs={
        #     "metadata": {
        #         "nested": {"path": "metadata"},
        #         "aggs": {
        #             "types": {
        #                 "terms": {"field": "metadata.type", "size": req.n_facets},
        #                 "aggs": {
        #                     "values": {
        #                         "terms": {
        #                             "field": "metadata.value",
        #                             "size": req.n_facets,
        #                             # "order": {"_key": "asc"},
        #                         }
        #                     }
        #                 },
        #             }
        #         },
        #     },
        #     "annotations": {
        #         "nested": {"path": "annotations"},
        #         "aggs": {
        #             "types": {
        #                 "terms": {"field": "annotations.type", "size": req.n_facets},
        #                 "aggs": {
        #                     "mentions": {
        #                         "terms": {
        #                             "field": "annotations.id_ER",
        #                             "size": req.n_facets,
        #                         },
        #                         "aggs": {
        #                             "top_hits_per_mention": {
        #                                 "top_hits": {
        #                                     "_source": [
        #                                         "annotations.display_name",
        #                                         "annotations.is_linked",
        #                                     ],
        #                                     "size": 1,
        #                                 }
        #                             }
        #                         },
        #                     }
        #                 },
        #             }
        #         },
        #     },
        # },
    )

    hits = get_hits(search_res)

    annotations_facets = get_facets_annotations_no_agg(search_res)

    # metadata_facets = get_facets_metadata(search_res)
    total_hits = search_res["hits"]["total"]["value"]
    num_pages = total_hits // req.documents_per_page
    if (
        total_hits % req.documents_per_page > 0
    ):  # if there is a remainder, add one more page
        num_pages += 1

    return {
        "hits": hits,
        "facets": {"annotations": annotations_facets, "metadata": []},
        "pagination": {
            "current_page": req.page,
            "total_pages": num_pages,
            "total_hits": total_hits,
        },
    }


if __name__ == "__main__":
    settings = get_settings()
    print(settings.dict())
    logger = logging.getLogger(__name__)

    # if not os.getenv("ENVIRONMENT", "production") == "dev":
    model = SentenceTransformer("intfloat/multilingual-e5-base", device="cuda")

    model = model.to(environ.get("SENTENCE_TRANSFORMER_DEVICE", "cuda"))
    print("model on device", model.device)
    model = model.eval()
    # chroma_client = chromadb.Client(
    #     Settings(
    #         chroma_server_host=settings.host_base_url,
    #         chroma_server_http_port=settings.chroma_port,
    #     )
    # )
    # collections = chroma_client.get_collections()

    # Print each collection
    # for collection in collections:
    #     print(collection)
    print("starting es client")
    es_client = Elasticsearch(
        hosts=[
            {
                # "host": (
                #     "es"
                #     if not os.getenv("ENVIRONMENT", "production") == "dev"
                #     else "localhost"
                # ),
                "host": "localhost",
                "scheme": "http",
                "port": int(settings.elastic_port),
            }
        ],
        request_timeout=60,
    )

    DOCS_BASE_URL = "http://" + "localhost" + ":" + "3001"
    print(DOCS_BASE_URL)
    retriever = DocumentRetriever(url=DOCS_BASE_URL + "/api/document")
    if not os.getenv("ENVIRONMENT", "production") == "dev":
        with open(environ.get("OGG2NAME_INDEX"), "r") as fd:
            ogg2name_index = json.load(fd)

    # [start fastapi]:
    _PORT = int(settings.indexer_server_port)
    uvicorn.run(app, host="0.0.0.0", port=_PORT)
