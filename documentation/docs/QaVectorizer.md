---
sidebar_position: 5
---

# qaVectorizer

This page contains all informations needed to start **qaVectorizer instance**. <br />
qaVectorizer is used to perform the **Faceted search** from the UI and to perform **retrieval** for the RAG module.

## Docker compose

You can start the **QaVectorizer instance** using **docker compose**.

```bash
sudo docker compose up -d qavectorizer
```

### Ports

Documents is accessible through port **3001** and documents_demo is accessible through port **3002**.

### ENV variables

In the **docker-compose.yml** you can edit the following ENV variables:

- `HOST_BASE_URL`: default base URL where all the previous services are running.
- `INDEXER_SERVER_PORT`: port to be used by qaVectorizer, the default value is `7863`
- `ELASTIC_PORT`: port to be used to connect to the ElasticSearch instance.
- `SENTENCE_TRANSFORMER_EMBEDDING_MODEL`: sentence transformer used to generate the embedding of the query to perform vector search in ElasticSearch.
- `NVIDIA_VISIBLE_DEVICES`: GPU to be used by the qaVectorizer, the default value is `all`.
