FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    TORCH_CUDA_ARCH_LIST="Pascal;Volta;Turing" \
    CUDA_HOME=/usr/local/cuda \
    PATH=$CUDA_HOME/bin:$PATH

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends wget libxml2-dev gnupg2 gcc g++ software-properties-common ninja-build \
    && wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin \
    && mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600 \
    && apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub \
    && add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /" \
    && apt-get update \
    && apt-get install -y --no-install-recommends cuda-toolkit-11-7 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./src .

RUN pip install --no-cache-dir -r ./requirements.txt

EXPOSE ${INDEXER_SERVER_PORT}

CMD python app.py
