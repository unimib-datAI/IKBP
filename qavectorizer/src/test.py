from actions import (
    count_chroma_collection_docs,
    get_chroma_collection,
    create_chroma_collection,
    delete_chroma_collection,
    index_chroma_document,
    delete_chroma_document,
    query_chroma,
    create_elastic_index,
    delete_elastic_index,
    index_elastic_document,
    query_elastic_index,
)

import json

# get_collection("test")
# count_collection_docs("test")
# print(create_chroma_collection("test"))
# print(delete_chroma_collection("test"))
# index_document(
#     "test",
#     {
#         "embeddings": [[6.7, 8.2, 9.2]],
#         "documents": ["This is a document"],
#         "metadatas": [{"source": "my_source"}],
#     },
# )
# delete_document("test", "id3")
# query_chroma("test", {"query": "immobile situato a prato"})

# es_client = Elasticsearch(
#     hosts=[{"host": "localhost", "scheme": "http", "port": 9200}], request_timeout=60
# )
# print(create_elastic_index("test"))
# print(delete_elastic_index("test"))
# index_elastic_document()
print(
    json.dumps(
        query_elastic_index(
            "test",
            {
                "text": "sentenza",
                # "annotations": [{"type": "persona", "value": "CTU"}],
                "page": 1,
                "n_facets": 10000,
            },
        ),
        indent=4,
    )
)

# res = query_elastic_index(
#     "test",
#     {
#         "text": "sentenza",
#         "annotations": [{"type": "persona", "value": "CTU"}],
#         # "metadata": [{"type": "anno sentenza", "value": "2021"}],
#         "page": 2,
#     },
# )

# print(len(res["hits"]))
