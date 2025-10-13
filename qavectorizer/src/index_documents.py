from tqdm import tqdm
import requests
from retriever import DocumentRetriever
from indexer import ChromaIndexer, ElasticsearchIndexer
from settings import AppSettings

settings = AppSettings()

DOCS_BASE_URL = "http://" + settings.host_base_url + ":" + settings.docs_port
INDEX_COLLECTION_NAME = settings.index_collection_name

retriever = DocumentRetriever(url=DOCS_BASE_URL + "/api/mongo/document")
chroma_indexer = ChromaIndexer(
    settings.embedding_model,
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)
elastic_indexer = ElasticsearchIndexer(anonymize_type=["persona", "parte", "controparte"])

# create indexes if they do not exist
chroma_indexer.create_index(INDEX_COLLECTION_NAME)
elastic_indexer.create_index(INDEX_COLLECTION_NAME)

print("Start indexing")
domains = ["famiglia"]#, "strada", "bancario"]
# index 100 documents for each domain
for domain in domains:
    documents = requests.get(DOCS_BASE_URL + "/api/mongo/document?limit=1000")
    documents = documents.json()["docs"]

    print("Indexing documents for domain: " + domain)
    for doc in tqdm(documents):
        doc_id = doc["id"]
        # retrieve a full document
        current_doc = retriever.retrieve(doc_id)
        # index chunks for the document
        chroma_indexer.index(
            collection="test",
            doc=current_doc,
            metadata={
                "doc_id": doc_id,
                "chunk_size": settings.chunk_size,
                "domain": domain,
            },
        )
        # index elastic

        # workaround to anonimize
        sensitive_types = set(['persona', 'parte', 'controparte', 'luogo', 'altro'])

        for ann in current_doc['annotation_sets']['entities_merged']['annotations']:
            if ann['type'] in sensitive_types or set(ann['features'].get('types', [])).intersection(sensitive_types):
                current_doc['text'] = current_doc['text'][:ann['start']] + "*" * (ann['end'] - ann['start']) + current_doc['text'][ann['end']:]

        elastic_indexer.index(index="test", doc=current_doc)
