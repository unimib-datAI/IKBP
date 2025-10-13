---
sidebar_position: 3
---

# ElasticSearch

This page contains all informations needed to start **ElasticSearch instance**. <br />
ElasticSearch will run by default on port **9201**.<br />
ElasticSearch is used to store all entities alongside of the documents, which are used to perform faceted search, and all embeddings for the text chunks relative to the documents, which are used in the retrieval phase of the RAG.

## Docker compose

You can start the **ElasticSearch instance** using **docker compose**.

```bash
sudo docker compose up -d es
```

<!--
### ENV variables

In the **docker-compose.yml** you can edit the following ENV variables:

- `MONGO_INITDB_ROOT_USERNAME`: default mongo root username
- `MONGO_INITDB_ROOT_PASSWORD`: default mongo root password
- `MONGO_INITDB_DATABASE`: default initial mongo database
- `MONGO_INITDB_USERNAME`: default mongo standard user username
- `MONGO_INITDB_PASSWORD`: default mongo standard user password -->
