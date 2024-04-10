FROM python:3

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --rabbiturl $RABBITURL \
                   --queue $RMQ_CLUSTERING \
                   --model $CLUSTERING_MODEL \
                   --timeout $CLUSTERING_TIMEOUT \
                   --max_memory $CLUSTERING_MAX_MEMORY
