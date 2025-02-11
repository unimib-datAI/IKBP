#!/bin/bash
python3 -m llama_cpp.server --model /models/Phi.gguf --chat_format chatml --n_gpu_layers 35 --n_ctx 20000 & 
python3 app.py -d ./models/${MODEL_NAME} -gl "${GPU_LAYERS}"
