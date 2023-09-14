# Documents indexer

#### DB

[https://docs.trychroma.com/]()

1. You can start using chromadb configured with a persistent directory, we will use a db
   whenever they fix this issue [https://github.com/chroma-core/chroma/issues/721]()
2. You can also run the server by follwing these commands:

Move to the chroma package directory:

```bash
cd ./packages/chroma
```

Run docker container

```bash
docker-compose up -d
```

Now the database is available on port `8000` and you can follow the instructions here: [https://docs.trychroma.com/usage-guide#running-chroma-in-clientserver-mode]()

#### Embedding model

We have to decide which model to use. But you can start to experiment with various models

#### Web server to expose the service

1. FastAPI
2. Endpoints:
   1. /index-document: single or bulk indexing
   2. /delete-document
   3. /search: retrieve top K most similar document given a natural language sentence
