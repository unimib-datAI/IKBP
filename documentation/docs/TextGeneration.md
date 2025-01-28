---
sidebar_position: 6
---

# Text Generation

This page contains all informations needed to start **Text generation instance**. <br />
Text generation is used to generate responses to user's questions, used inside the RAG module.

## Docker compose

You can start the **Text Generation instance** using **docker compose**.

```bash
sudo docker compose up -d text-generation
```

### Ports

Text generation is accessible through port **7862**.

### ENV variables

In the **docker-compose.yml** you can edit the following ENV variables:

- `GPU_LAYERS`: parameter to select how much gpu layers should be used during text generation, default value is `-1` which uses all gpus available.
