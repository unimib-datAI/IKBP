import requests
from requests.exceptions import HTTPError
from settings import AppSettings

settings = AppSettings()

INDEXER_BASE_URL = (
    "http://" + settings.host_base_url + ":" + settings.indexer_server_port
)


def create_elastic_index(name):
    data = {
        "name": name,
    }

    try:
        r = requests.post(INDEXER_BASE_URL + "/elastic/index", json=data)
        return r.json()
    except HTTPError as e:
        print(e)


def index_elastic_document(index_name, document):
    try:
        r = requests.post(
            INDEXER_BASE_URL
            + "/elastic/index/{index_name}/doc".replace("{index_name}", index_name),
            json={"doc": document},
        )
        return r.json()
    except HTTPError as e:
        print(e)


def delete_elastic_index(name):
    try:
        r = requests.delete(
            INDEXER_BASE_URL + "/elastic/index/{name}".replace("{name}", name)
        )
        return r.json()
    except HTTPError as e:
        print(e)


def create_chroma_collection(name):
    data = {
        "name": name,
    }

    try:
        r = requests.post(INDEXER_BASE_URL + "/chroma/collection", json=data)
        return r.json()
    except HTTPError as e:
        print(e)


def delete_chroma_collection(name):
    try:
        r = requests.delete(
            INDEXER_BASE_URL + "/chroma/collection/{name}".replace("{name}", name)
        )
        return r.json()
    except HTTPError as e:
        print(e)


def get_chroma_collection(name):
    try:
        r = requests.get(
            INDEXER_BASE_URL + "/chroma/collection/{name}".replace("{name}", name)
        )
        return r.json()
    except HTTPError as e:
        print(e)


def count_chroma_collection_docs(collection_name):
    try:
        r = requests.get(
            INDEXER_BASE_URL
            + "/chroma/collection/{collection_name}/count".replace(
                "{collection_name}", collection_name
            )
        )
        return r.json()
    except HTTPError as e:
        print(e)


def index_chroma_document(collection_name, document):
    return requests.post(
        INDEXER_BASE_URL
        + "/chroma/collection/{collection_name}/doc".replace(
            "{collection_name}", collection_name
        ),
        json=document,
    )


def delete_chroma_document(collection_name, document_id):
    try:
        r = requests.delete(
            INDEXER_BASE_URL
            + "/chroma/collection/{collection_name}/doc/{document_id}".replace(
                "{collection_name}", collection_name
            ).replace("{document_id}", document_id)
        )
        return r.json()
    except HTTPError as e:
        print(e)


def query_chroma(collection_name, options):
    try:
        r = requests.post(
            INDEXER_BASE_URL
            + "/chroma/collection/{collection_name}/query".replace(
                "{collection_name}", collection_name
            ),
            json=options,
        )
        return r.json()
    except HTTPError as e:
        print(e)


def query_elastic_index(index_name, options):
    try:
        r = requests.post(
            INDEXER_BASE_URL
            + "/elastic/index/{index_name}/query".replace("{index_name}", index_name),
            json=options,
        )
        return r.json()
    except HTTPError as e:
        print(e)


def add_annotations_to_document(index_name, document_id, mentions):
    """
    Add or remove annotations to/from a document in Elasticsearch.

    Args:
        index_name (str): The name of the Elasticsearch index
        document_id (str): The ID of the document to update
        mentions (list): A list of mention objects to add as annotations.
                         Each mention can include a "to_delete" boolean flag
                         to indicate if it should be removed instead of added.

    Returns:
        dict: The response from the API containing:
            - result: The Elasticsearch operation result
            - document_id: The ID of the updated document
            - annotations_added: Number of annotations added
            - annotations_removed: Number of annotations removed
    """
    try:
        r = requests.post(
            INDEXER_BASE_URL
            + "/elastic/index/{index_name}/doc/{document_id}/annotations".replace(
                "{index_name}", index_name
            ).replace(
                "{document_id}", document_id
            ),
            json={"mentions": mentions},
        )
        return r.json()
    except HTTPError as e:
        print(e)
        return {"error": str(e)}
