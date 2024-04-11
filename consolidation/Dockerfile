FROM python:3

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --rabbiturl $RABBITURL \
                   --queue $RMQ_CONSOLIDATION \
                   --timeout $CONSOLIDATION_TIMEOUT \
                   --max_memory $CONSOLIDATION_MAX_MEMORY