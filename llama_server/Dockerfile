# Use an official Ubuntu as a parent image
ARG CUDA_IMAGE="12.2.2-devel-ubuntu22.04"
FROM nvidia/cuda:${CUDA_IMAGE}

# Set the working directory in the container
WORKDIR /app

# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone the Llama.cpp repository
RUN git clone https://github.com/ggerganov/llama.cpp.git

# Build Llama.cpp using CMake
WORKDIR /app/llama.cpp
RUN cmake -B build -DGGML_CUDA=ON && \
    cmake --build build --config Release -- -j$(nproc)

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["./main", "--model", "/models/Phi-3.5-mini-ITA.Q8_0.gguf", "--n-gpu-layers", "-1"]
