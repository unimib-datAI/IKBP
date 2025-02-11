from elasticsearch import Elasticsearch
import uvicorn
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends
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
    group_facets,
    collect_chunk_ranks,
    collect_chunk_ranks_full_text,
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


class CreateCollectionRequest(BaseModel):
    name: str


class IndexDocumentRequest(BaseModel):
    embeddings: List[List[float]]
    documents: List[str]
    metadatas: List[dict] = []


class QueryCollectionRquest(BaseModel):
    query: str
    filter_ids: List[str] = []
    k: int = 5
    where: dict = None
    include: List[str] = ["metadatas", "documents", "distances"]
    retrievalMethod: str = "full"


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

    embeddings = []
    print("query", req.dict())
    with torch.no_grad():
        # create embeddings for the query
        embeddings = model.encode(req.query)
    embeddings = embeddings.tolist()
    print(len(embeddings))
    query_body = None
    query_full_text = None

    if hasattr(req, "filter_ids") and len(req.filter_ids) > 0:
        query_body = {
            "knn": {
                "inner_hits": {
                    "_source": False,
                    "fields": ["chunks.vectors.text", "_score"],
                    # "size": 10,
                },
                "field": "chunks.vectors.predicted_value",
                "query_vector": embeddings,
                "k": 5,
                # "num_candidates": 1000,
                "filter": {"terms": {"id": [doc_id for doc_id in req.filter_ids]}},
            },
        }

        # excludes ner entities search if specified in retrieval method
        should_query = (
            [
                {
                    "match": {
                        "chunks.vectors.text": req.query,
                    }
                },
            ]
            if req.retrievalMethod == "hibrid_no_ner"
            else [
                {"match": {"chunks.vectors.text": req.query}},
                {
                    "match": {
                        "chunks.vectors.entities": req.query,
                    }
                },
            ]
        )
        q = {
            "_source": True,
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"id": [doc_id for doc_id in req.filter_ids]}}
                    ],
                    "must": [
                        {
                            "nested": {
                                "path": "chunks",
                                "query": {
                                    "nested": {
                                        "path": "chunks.vectors",
                                        "query": {
                                            "bool": {
                                                "should": should_query,
                                            }
                                        },
                                    }
                                },
                                "inner_hits": {
                                    "_source": False,
                                    "fields": ["chunks.vectors.text", "_score"],
                                },
                            }
                        }
                    ],
                },
            },
        }
        query_full_text = {
            "_source": ["id"],
            "query": {
                "nested": {
                    "path": "chunks.vectors",
                    "query": {
                        "bool": {
                            "must": [
                                {"bool": {"should": should_query}},
                                {
                                    "terms": {
                                        "id": [doc_id for doc_id in req.filter_ids]
                                    }
                                },
                            ]
                        }
                    },
                    "inner_hits": {
                        "_source": False,
                        "fields": ["chunks.vectors.text", "_score"],
                    },
                }
            },
        }

    else:
        query_body = {
            "_source": ["id"],
            "knn": {
                "inner_hits": {
                    "_source": False,
                    "fields": ["chunks.vectors.text", "_score"],
                },
                "field": "chunks.vectors.predicted_value",
                "query_vector": embeddings,
                "k": 5,
            },
        }

        # excludes ner entities search if specified in retrieval method
        should_query = (
            [
                {"match": {"chunks.vectors.text": req.query}},
            ]
            if req.retrievalMethod == "hibrid_no_ner"
            else [
                {
                    "match": {
                        "chunks.vectors.text": req.query,
                    }
                },
                {
                    "match": {
                        "chunks.vectors.entities": req.query,
                    }
                },
            ]
        )
        q = {
            "_source": True,
            "query": {
                "bool": {
                    # "filter": [
                    #     {
                    #         "terms": {
                    #             "id": [
                    #                 "e45a49ff92fe4c11a9455a66b5c8ced89b3d4e844db9b8c05bfd738524a40bcb"
                    #             ]
                    #         }
                    #     }
                    # ],
                    "must": [
                        {
                            "nested": {
                                "path": "chunks",
                                "query": {
                                    "nested": {
                                        "path": "chunks.vectors",
                                        "query": {
                                            "bool": {
                                                "should": should_query,
                                            }
                                        },
                                    }
                                },
                                "inner_hits": {
                                    "_source": False,
                                    "fields": ["chunks.vectors.text", "_score"],
                                },
                            }
                        }
                    ],
                },
            },
        }
        query_full_text = {
            "_source": ["id"],
            "query": {
                "nested": {
                    "path": "chunks.vectors",
                    "query": {"bool": {"should": should_query}},
                    "inner_hits": {
                        "_source": False,
                        "fields": ["chunks.vectors.text", "_score"],
                    },
                },
            },
        }

    results = (
        es_client.search(index=collection_name, body=query_body)
        if req.retrievalMethod == "full"
        or req.retrievalMethod == "dense"
        or req.retrievalMethod == "hibrid_no_ner"
        else []
    )

    # debug print statement for checking correct retrieval mode
    if (
        req.retrievalMethod != "full"
        and req.retrievalMethod != "hibrid_no_ner"
        and req.retrievalMethod != "dense"
    ):
        print("results", results)

    # debug print statement for checking correct retrieval mode
    response_full_text = (
        es_client.search(index=collection_name, body=q)
        if req.retrievalMethod == "full"
        or req.retrievalMethod == "hibrid_no_ner"
        or req.retrievalMethod == "full-text"
        else []
    )
    if (
        req.retrievalMethod != "full"
        and req.retrievalMethod != "hibrid_no_ner"
        and req.retrievalMethod != "full-text"
    ):
        print("response_full_text", response_full_text)
    del embeddings
    print("query", q)

    # Get chunk-level ranks for both searches
    vector_ranks = collect_chunk_ranks(results) if len(results) > 0 else {}
    full_text_ranks = (
        collect_chunk_ranks_full_text(response_full_text)
        if len(response_full_text) > 0
        else {}
    )
    print("FT Ranks", full_text_ranks, len(response_full_text))

    # RRF Parameters
    rrf_k = 60  # Adjust as needed

    # Combine ranks using RRF at the chunk level
    combined_scores = {}
    all_chunk_ids = set(vector_ranks.keys()).union(full_text_ranks.keys())

    for chunk_id in all_chunk_ids:
        rank_vector = vector_ranks.get(chunk_id, float("inf"))
        rank_full_text = full_text_ranks.get(chunk_id, float("inf"))
        combined_scores[chunk_id] = (1 / (rrf_k + rank_vector)) + (
            1 / (rrf_k + rank_full_text)
        )

    # Sort chunks by combined RRF scores
    final_ranking = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    print("final_ranking", final_ranking)
    # for rank, (doc_id, score) in enumerate(final_ranking[:20], start=1):
    #     print(f"Rank: {rank}, Doc ID: {doc_id}, RRF Score: {score}")

    doc_chunks_id_map = {}

    for chunk in final_ranking[:15]:
        doc_id = chunk[0][0]
        temp_chunk = {
            "id": doc_id,
            "text": chunk[0][1],
            "metadata": {"doc_id": doc_id, "chunk_size": len(chunk[0][1])},
        }
        if doc_id in doc_chunks_id_map:
            doc_chunks_id_map[doc_id].append(temp_chunk)
        else:
            doc_chunks_id_map[doc_id] = [temp_chunk]
    full_docs = []

    # get full documents from db
    doc_ids = list(doc_chunks_id_map.keys())
    current_retriever = retriever
    if collection_name == "bologna":
        current_retriever = retriever_bologna
    elif collection_name == "sperimentazione":
        current_retriever = retriever_sperimentazione
    for doc_id in doc_ids:
        d = current_retriever.retrieve(doc_id)
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
    print(doc_chunks_id_map.keys())
    if len(req.filter_ids) == 1:
        temp_chunk = {
            "id": full_docs[0]["id"],
            "text": full_docs[0]["text"],
            "metadata": {
                "doc_id": full_docs[0]["id"],
                "chunk_size": len(full_docs[0]["text"]),
            },
        }
        doc_results.append(
            {
                "doc": full_docs[0],
                "chunks": [temp_chunk],
            }
        )
        return doc_results
    for doc in full_docs:
        print(doc.keys())
        doc_results.append({"doc": doc, "chunks": doc_chunks_id_map[doc["id"]]})

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
    from_offset = (req.page - 1) * req.documents_per_page

    query = {
        "bool": {
            "must": [{"query_string": {"query": req.text, "default_field": "text"}}],
            "filter": {"bool": {"should": []}},
        },
    }
    if req.text == "" or req.text == None or req.text == " ":
        query["bool"]["must"] = [{"match_all": {}}]
    # print("annotations", req.annotations)
    if req.annotations != None and len(req.annotations) > 0:
        for annotation in req.annotations:
            query["bool"]["filter"]["bool"]["should"].append(
                {
                    "nested": {
                        "path": "annotations",
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "term": {
                                            "annotations.id_ER": annotation["value"]
                                        }
                                    },
                                    {"term": {"annotations.type": annotation["type"]}},
                                ],
                            }
                        },
                    }
                },
            )

    if req.metadata != None and len(req.metadata) > 0:
        for metadata in req.metadata:
            query["bool"]["filter"]["bool"]["should"].append(
                {
                    "nested": {
                        "path": "metadata",
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"metadata.value": metadata["value"]}},
                                    {"term": {"metadata.type": metadata["type"]}},
                                ],
                            }
                        },
                    }
                },
            )
    # get all docs if req.text is empty
    # if (req.text == "" or req.text == None or req.text == " ") and (req.metadata == None or len(req.metadata) == 0) and (req.annotations == None or len(req.annotations) == 0):

    search_res = es_client.search(
        index=index_name,
        size=20,
        source_excludes=["chunks"],
        from_=from_offset,
        query=query,
    )

    hits = get_hits(search_res)

    annotations_facets = get_facets_annotations_no_agg(search_res)
    annotations_facets = group_facets(annotations_facets)
    metadata_facets = get_facets_metadata(search_res)
    total_hits = search_res["hits"]["total"]["value"]

    num_pages = total_hits // req.documents_per_page
    if (
        total_hits % req.documents_per_page > 0
    ):  # if there is a remainder, add one more page
        num_pages += 1
    return {
        "hits": hits,
        "facets": {"annotations": annotations_facets, "metadata": metadata_facets},
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
    model = SentenceTransformer(
        environ.get(
            "SENTENCE_TRANSFORMER_EMBEDDING_MODEL", "Alibaba-NLP/gte-multilingual-base"
        ),
        device="cuda",
        trust_remote_code=True,
    )
    model = model.to(environ.get("SENTENCE_TRANSFORMER_DEVICE", "cuda"))
    print("model on device", model.device)
    model = model.eval()

    # Print each collection
    # for collection in collections:
    #     print(collection)
    print(
        "starting es client",
        {
            "host": "localhost",
            "scheme": "http",
            "port": 9201,
        },
    )
    es_client = Elasticsearch(
        hosts=[
            {
                "host": "es",
                "scheme": "http",
                "port": 9200,
            }
        ],
        request_timeout=60,
    )

    DOCS_BASE_URL = "http://" + "documents" + ":" + "3001"
    # for bologna  "http://" + "10.0.0.108" + ":" + "3002"
    BOLOGNA_DOCS_BASE_URL = "http://" + "10.0.0.108" + ":" + "3002"
    SPERIMENTAZIONE_DOCS_BASE_URL = "http://" + "10.0.0.108" + ":" + "3003"
    print(DOCS_BASE_URL)
    retriever = DocumentRetriever(url=DOCS_BASE_URL + "/api/document")
    retriever_bologna = DocumentRetriever(url=BOLOGNA_DOCS_BASE_URL + "/api/document")
    retriever_sperimentazione = DocumentRetriever(
        url=SPERIMENTAZIONE_DOCS_BASE_URL + "/api/document"
    )
    # if not os.getenv("ENVIRONMENT", "production") == "dev":
    #     with open(environ.get("OGG2NAME_INDEX"), "r") as fd:
    #         ogg2name_index = json.load(fd)

    # [start fastapi]:
    _PORT = int(settings.indexer_server_port)
    uvicorn.run(app, host="0.0.0.0", port=_PORT)
