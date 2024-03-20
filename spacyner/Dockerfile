FROM pytorch/pytorch:1.11.0-cuda11.3-cudnn8-runtime

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --rabbiturl $RABBITURL --queue $RMQ_SPACY --timeout $SPACY_TIMEOUT --model $SPACY_MODEL --tag $SPACY_TAG $SPACY_ARGS
