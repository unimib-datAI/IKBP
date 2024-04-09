FROM rpozzi/blink:devel

# Upgrade PIP
RUN python3 -m pip install --upgrade pip

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --rabbiturl $RABBITURL --queue $RMQ_BIENCODER --biencoder_model $BIENCODER_MODEL --biencoder_config $BIENCODER_CONFIG --timeout $BIENCODER_TIMEOUT --max_memory $BIENCODER_MAX_MEMORY --max_gpu $BIENCODER_MAX_GPU

