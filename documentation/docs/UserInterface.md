---
sidebar_position: 7
---

# User Interface

This page contains all informations needed to start **User Interface instance**. <br />
The user interface have two variants, one for demo purpose.

## Docker compose

You can start the **User interface instance** using **docker compose**.

```bash
sudo docker compose up -d ui
```

Or

```bash
sudo docker compose up -d ui_demo
```

### Ports

The User Interface is accessible through port **13001** or port **13002** for the demo version.

### ENV variables

In the **docker-compose.yml** you can edit the following ENV variables:

- `ACCESS_USERNAME`: username used to login in the user interface.
- `ACCESS_PASSWORD`: password used to login in the user interface.
- `API_BASE_URI`: base url used to call the documents service.
- `NEXTAUTH_SECRET`: secret used to verify user session.
- `NEXTAUTH_URL`: url used to manage authentication by the User Interface.
- `NEXT_PUBLIC_BASE_PATH`: User interface base relative url.
- `NEXT_PUBLIC_FULL_PATH`: User interface base full url.
- `TEXT_GENERATION`: address of the `text-generation` service.
- `API_INDEXER`: address of the `qavectorizer` service.
