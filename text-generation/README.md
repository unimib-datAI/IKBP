# Text generation service using a LLM

#### Models

The architecture can be expanded, but at the moment I can use any hugging face model that is quantized using GPTQ. Inference is fast thanks to Exllama.

At the moment I tried the following models:

* wizard-vicuna-13B-GPTQ
* Wizard-Vicuna-13B-Uncensored-GPTQ
* robin-13B-v2-GPTQ

You can set MODEL_NAME env variable e restart the docker container with:

```bash
docker-compose up -d
```

#### Web server to expose the service

1. FastAPI
2. Endpoints:
   1. /generate: generate text sequence given inputs and optionally model parameters
