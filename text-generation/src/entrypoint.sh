#!/bin/bash
python3 -m llama_cpp.server --model /models/Phi4.gguf --chat_format chatml --n_gpu_layers -1 --n_ctx 18000 --n_threads -1 &
# ollama serve &
# ollama run phi4-mini &
python3 app.py -d ./models/${MODEL_NAME} -gl -1
