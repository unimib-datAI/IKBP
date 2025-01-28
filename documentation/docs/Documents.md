---
sidebar_position: 4
---

# Documents

This page contains all informations needed to start **Documents instance**. <br />
There are two different instances available, one for demo purpose and the other to real use purpose. The current demo version serves documents relative to the _Bologna's massacre_.<br />
Documents is used to retrieve and update the annotated documents.

## Docker compose

You can start the **ElasticSearch instance** using **docker compose**.

```bash
sudo docker compose up -d documents
```

Or

```bash
sudo docker compose up -d documents_demo
```

### Ports

Documents is accessible through port **3001** and documents_demo is accessible through port **3002**.

### ENV variables

In the **docker-compose.yml** you can edit the following ENV variables:

- `MONGO`: MongoDB connection string, the demo and regular version must use different connection string, and the connection string must specify the correct database.
