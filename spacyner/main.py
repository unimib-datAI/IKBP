import argparse
from pydantic import BaseModel
import spacy
from spacy.cli import download as spacy_download
import os
from gatenlp import Document
import pika
import timeout_decorator
import json
import traceback

DEFAULT_TAG='aplha_v0.1.0_spacy'
model = ''
tag = 'merged'
senter = False
spacy_pipeline = None
gpu_id = -1

class Item(BaseModel):
    text: str

def restructure_newline(text):
  return text.replace('\n', ' ')

def encode_mention(doc: dict):
    global model
    global senter
    global tag
    global spacy_pipeline

    # replace wrong newlines
    text = restructure_newline(doc['text'])

    doc = Document.from_dict(doc)
    entity_set = doc.annset('entities_{}'.format(tag))

    spacy_out = spacy_pipeline(text)

    # sentences
    if senter:
        sentence_set = doc.annset('sentences_{}'.format(tag))
        for sent in spacy_out.sents:
            # TODO keep track of entities in this sentence?
            sentence_set.add(sent.start_char, sent.end_char, "sentence", {
                "source": "spacy",
                "spacy_model": model
            })

    for ent in spacy_out.ents:
        # TODO keep track of sentences
        # sentence_set.overlapping(ent.start_char, ent.end_char)
        feat_to_add = {
            "ner": {
                "type": ent.label_,
                "score": 1.0,
                "source": "spacy",
                "spacy_model": model
                }}
        if ent.label_ == 'DATE':
            feat_to_add['linking'] = {
                "skip": True
            }

        entity_set.add(ent.start_char, ent.end_char, ent.label_, feat_to_add)

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []
    doc.features['pipeline'].append('spacyner')

    return doc.to_dict()

def initialize():
    global model
    global senter
    global spacy_pipeline
    global gpu_id
    print('Loading spacy model...')
    # Load spacy model
    try:
        spacy_pipeline = spacy.load(model, exclude=['tok2vec', 'morphologizer', 'tagger', 'parser', 'attribute_ruler', 'lemmatizer'])
    except Exception as e:
        print('Caught exception:', e, '... Trying to download spacy model ...')
        spacy_download(model)
        spacy_pipeline = spacy.load(model, exclude=['tok2vec', 'morphologizer', 'tagger', 'parser', 'attribute_ruler', 'lemmatizer'])

    # gpu
    if gpu_id >= 0:
        gpu = spacy.prefer_gpu(gpu_id)
        print('Using', f'gpu {gpu}' if gpu else 'cpu', flush=True)

    # sentences
    if senter:
        spacy_pipeline.enable_pipe('senter')

    print('Loading complete.')


################## rmq

def queue_doc_in_callback(ch, method, properties, body):
    print("[x] Received doc")
    body = json.loads(body.decode())

    @timeout_decorator.timeout(TIMEOUT)
    def timeout_encode_mention(body):
        return encode_mention(body)

    try:
        #doc = func_timeout(TIMEOUT, encode_mention_from_doc, args=(body))
        doc = timeout_encode_mention(body)

        ch.basic_publish(exchange='', routing_key=QUEUES['doc_out'], body=json.dumps(doc))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except timeout_decorator.TimeoutError:
        print("DOC could not complete within timeout and was terminated.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        ch.basic_publish(exchange='', routing_key=QUEUES['errors'], body=json.dumps({
            'from': QUEUES['doc_in'],
            'reason': 'timeout',
            'body': body
        }))
    except Exception as exc_obj:
        pipeline_tb = traceback.format_exc()
        print("DOC exception:", pipeline_tb)

        ch.basic_publish(exchange='', routing_key=QUEUES['errors'], body=json.dumps({
            'from': QUEUES['doc_in'],
            'reason': pipeline_tb,
            'body': body
        }))

        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default="en_core_web_sm", help="spacy model to load",
    )
    parser.add_argument(
        "--tag", type=str, default=DEFAULT_TAG, help="AnnotationSet tag",
    )
    parser.add_argument(
        "--sents", action='store_true', default=False, help="Do sentence tokenization",
    )
    parser.add_argument(
        "--gpu-id", type=int, default=-1, help="Spacy GPU id",
    )
    parser.add_argument(
        "--rabbiturl", type=str, default='amqp://guest:guest@rabbitmq:5672/', help="rabbitmq url",
    )
    parser.add_argument(
        "--queue", type=str, default="spacyner", help="rabbitmq queue root",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="timeout in seconds",
    )

    args = parser.parse_args()

    model = args.model
    senter = args.sents
    tag = args.tag
    gpu_id = args.gpu_id
    TIMEOUT = args.timeout

    initialize()

    # RabbitMQ connection parameters
    RMQ_URL = args.rabbiturl
    QUEUE_ROOT = args.queue
    TIMEOUT = args.timeout

    QUEUES = {
        'doc_in': '{root}/doc/in',
        'doc_out': '{root}/doc/out',
        'errors': '{root}/errors'
    }
    
    for k in QUEUES:
        QUEUES[k] = QUEUES[k].format(root=QUEUE_ROOT)

    # Connect to RabbitMQ server
    parameters = pika.URLParameters(RMQ_URL)
    parameters.heartbeat = TIMEOUT + 1
    parameters.blocked_connection_timeout = TIMEOUT + 1
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()


    channel.basic_qos(prefetch_count=1)

    channel.queue_declare(queue=QUEUES['doc_in'])

    channel.queue_declare(queue=QUEUES['doc_out'])

    channel.queue_declare(queue=QUEUES['errors'])

    # Set up the consumer
    channel.basic_consume(queue=QUEUES['doc_in'], on_message_callback=queue_doc_in_callback, auto_ack=False)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    # Start consuming messages
    channel.start_consuming()
