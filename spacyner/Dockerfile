FROM pytorch/pytorch:1.11.0-cuda11.3-cudnn8-runtime

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD gunicorn -w "$SPACY_WORKERS" main:app -b 0.0.0.0:80 -k uvicorn.workers.UvicornWorker --timeout $SPACY_TIMEOUT --capture-output
