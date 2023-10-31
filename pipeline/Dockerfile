FROM python:3.11

WORKDIR /home/app

RUN pip install --upgrade pip

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD gunicorn -w "$WORKERS" main:app -b 0.0.0.0:80 -k uvicorn.workers.UvicornWorker --timeout $TIMEOUT --capture-output
