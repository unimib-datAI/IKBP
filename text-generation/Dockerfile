ARG CUDA_IMAGE="12.2.2-devel-ubuntu22.04"
FROM nvidia/cuda:${CUDA_IMAGE}

# Set the host to 0.0.0.0 for external access
ENV HOST 0.0.0.0
RUN apt-get clean && rm -rf /var/lib/apt/lists/*


RUN apt-get update --allow-insecure-repositories && apt-get upgrade -y --allow-unauthenticated \
    && apt-get install -y git build-essential \
    python3 curl tar python3-pip gcc wget unzip \
    ocl-icd-opencl-dev opencl-headers clinfo \
    libclblast-dev libopenblas-dev \
    && mkdir -p /etc/OpenCL/vendors && echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
RUN dpkg -i cuda-keyring_1.0-1_all.deb
# Set build-related env vars
ENV CUDA_DOCKER_ARCH=all
ENV LLAMA_CUBLAS=1

# Install dependencies
RUN python3 -m pip install --upgrade pip pytest cmake scikit-build setuptools fastapi uvicorn sse-starlette pydantic-settings starlette-context

# Download the latest llama.cpp release binaries
WORKDIR /workspace
# RUN wget -qO- https://api.github.com/repos/ggerganov/llama.cpp/releases/latest | \
#     grep "browser_download_url.*llama.*linux-x86_64" | \
#     cut -d '"' -f 4 | wget -i - -O llama.cpp.tar.gz && \
#     tar -xzf llama.cpp.tar.gz && \
#     rm llama.cpp.tar.gz && \
#     chmod +x ./llama.cpp
ENV PATH="/usr/local:${PATH}"
# Install Ollama
# RUN curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz
# RUN tar -C /usr -xzf ollama-linux-amd64.tgz
# RUN sudo curl -fsSL https://ollama.com/install.sh |  bash
# RUN find / -type f -name 'ollama' -exec echo 'Found ollama at: {}' \;

# Install llama-cpp-python (build with CUDA)
# #for Tesla T4
ENV DCMAKE_CUDA_ARCHITECTURES=75
ENV CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=75"
RUN pip install --upgrade --no-cache-dir llama-cpp-python 'llama-cpp-python[server]' langchain openai langchain_community langchain-openai langchain-ollama


WORKDIR /workspace

COPY ./requirements.txt ./src .

RUN pip install --no-cache-dir -r ./requirements.txt

EXPOSE 7862
ENTRYPOINT ["./entrypoint.sh"]

# CMD python3 -m llama_cpp.server --model /models/Phi.gguf --chat_format chatml --n_gpu_layers 35
# CMD python3 app.py -d ./models/${MODEL_NAME} -gl "${GPU_LAYERS}"
