FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

WORKDIR /home/app

COPY ./src .

RUN apt-get update && apt-get install --no-install-recommends -y git && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

EXPOSE 7862

CMD gunicorn -w "$TEXT_GENERATION_WORKERS" app:app -b 0.0.0.0:80 -k uvicorn.workers.UvicornWorker --timeout $TEXT_GENERATION_TIMEOUT --capture-output