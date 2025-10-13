FROM python:3

WORKDIR /home/app

COPY . .
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libatlas-base-dev \
    gfortran \
    libopenblas-dev \
    cython3
RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --host 0.0.0.0 --port 80 --model $CLUSTERING_MODEL