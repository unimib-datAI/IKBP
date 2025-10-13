---
sidebar_position: 2
---

# MongoDB

This page contains all informations needed to start **MongoDB instance**. <br />
Mongo will run by default on port **27017**.<br />
MongoDB is used to store all annotated documents.

## Docker compose

You can start the **MongoDB instance** using **docker compose**.

```bash
sudo docker compose up -d mongo
```

### ENV variables

In the **docker-compose.yml** you can edit the following ENV variables:

- `MONGO_INITDB_ROOT_USERNAME`: default mongo root username
- `MONGO_INITDB_ROOT_PASSWORD`: default mongo root password
- `MONGO_INITDB_DATABASE`: default initial mongo database
- `MONGO_INITDB_USERNAME`: default mongo standard user username
- `MONGO_INITDB_PASSWORD`: default mongo standard user password
