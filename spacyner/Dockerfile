
FROM pytorch/pytorch:1.11.0-cuda11.3-cudnn8-runtime

WORKDIR /home/app

COPY . .

# Install build-essential for g++ and other compilers needed for spaCy dependencies
RUN apt-get update && apt-get install -y build-essential

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD gunicorn -w "$SPACY_WORKERS" main:app -b 0.0.0.0:80 -k uvicorn.workers.UvicornWorker --timeout $SPACY_TIMEOUT --capture-output
