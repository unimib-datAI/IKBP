import argparse
from pydantic import BaseModel
from blink.main_dense import load_biencoder, _process_biencoder_dataloader
from blink.biencoder.eval_biencoder import get_candidate_pool_tensor
from typing import List, Optional
import json
from tqdm import tqdm
import torch
import numpy as np
import base64
import logging
from torch.utils.data import DataLoader, SequentialSampler
from gatenlp import Document
import pika
import timeout_decorator
import traceback

def vector_encode(v):
    s = base64.b64encode(v).decode()
    return s

def vector_decode(s, dtype=np.float32):
    buffer = base64.b64decode(s)
    v = np.frombuffer(buffer, dtype=dtype)
    return v

class Mention(BaseModel):
    label: str = 'unknown'
    label_id: int = -1
    context_left: str
    context_right:str
    mention: str
    start_pos: Optional[int]
    end_pos: Optional[int]
    sent_idx: Optional[int]

class Entity(BaseModel):
    title: str
    descr: str

# remember `content-type: application/json`
def encode_mention_from_doc(doc: dict):
    doc = Document.from_dict(doc)

    annsets_to_link = set([doc.features.get('annsets_to_link', 'entities_merged')])

    samples = []
    mentions = []

    for annset_name in set(doc.annset_names()).intersection(annsets_to_link):
        # if not annset_name.startswith('entities'):
        #     # considering only annotation sets of entities
        #     continue
        for mention in doc.annset(annset_name):
            if 'linking' in mention.features and mention.features['linking'].get('skip', False):
                # DATES should skip = true bcs linking useless
                continue
            blink_dict = {
                # TODO use sentence instead of document?
                # TODO test with very big context
                'context_left': mention.features['context_left'] if 'context_left' in mention.features \
                                                                    else doc.text[:mention.start],
                'context_right': mention.features['context_right'] if 'context_right' in mention.features \
                                                                    else doc.text[mention.end:],
                'mention': mention.features['mention'] if 'mention' in mention.features \
                                                                    else doc.text[mention.start:mention.end],
                #
                'label': 'unknown',
                'label_id': -1,
            }
            samples.append(blink_dict)
            mentions.append(mention)

    dataloader = _process_biencoder_dataloader(
        samples, biencoder.tokenizer, biencoder_params
    )
    encodings = _run_biencoder_mention(biencoder, dataloader)
    if len(encodings) > 0:
        assert encodings[0].dtype == 'float32'
    encodings = [vector_encode(e) for e in encodings]

    for mention, enc in zip(mentions, encodings):
        mention.features['linking'] = {
            'encoding': enc,
            'source': 'blink_biencoder'
        }

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []
    doc.features['pipeline'].append('biencoder')

    return doc.to_dict()

def encode_mention(samples: List[Mention]):
    samples = [dict(s) for s in samples]
    dataloader = _process_biencoder_dataloader(
        samples, biencoder.tokenizer, biencoder_params
    )
    encodings = _run_biencoder_mention(biencoder, dataloader)
    if len(encodings) > 0:
        assert encodings[0].dtype == 'float32'
    #assert np.array_equal(encodings[0], vector_decode(vector_encode(encodings[0]), np.float32))
    ## dtype float32
    encodings = [vector_encode(e) for e in encodings]
    return {'samples': samples, 'encodings': encodings}

def encode_entity(samples: List[Entity]):
    # entity_desc_list: list of tuples (title, text)
    entity_desc_list = [(s.title, s.descr) for s in samples]
    candidate_pool = get_candidate_pool_tensor(
        entity_desc_list,
        biencoder.tokenizer,
        biencoder_params["max_cand_length"],
        logger
    )
    sampler = SequentialSampler(candidate_pool)
    dataloader = DataLoader(
        candidate_pool, sampler=sampler, batch_size=8
    )

    encodings = _run_biencoder_entity(biencoder, dataloader)

    if len(encodings) > 0:
        assert encodings[0].dtype == 'float32'
    #assert np.array_equal(encodings[0], vector_decode(vector_encode(encodings[0]), np.float32))
    ## dtype float32
    encodings = [vector_encode(e) for e in encodings]
    return {'samples': samples, 'encodings': encodings}

def _run_biencoder_mention(biencoder, dataloader):
    biencoder.model.eval()
    encodings = []
    for batch in tqdm(dataloader):
        context_input, _, _ = batch
        with torch.no_grad():
            context_input = context_input.to(biencoder.device)
            context_encoding = biencoder.encode_context(context_input).numpy()
            context_encoding = np.ascontiguousarray(context_encoding)
        encodings.extend(context_encoding)
    return encodings

def _run_biencoder_entity(biencoder, dataloader):
    biencoder.model.eval()
    cand_encode_list = []
    for batch in tqdm(dataloader):
        cands = batch
        cands = cands.to(biencoder.device)
        with torch.no_grad():
            cand_encode = biencoder.encode_candidate(cands).numpy()
            cand_encode = np.ascontiguousarray(cand_encode)
        cand_encode_list.extend(cand_encode)
    return cand_encode_list

def load_models(args):
    # load biencoder model
    with open(args.biencoder_config) as json_file:
        biencoder_params = json.load(json_file)
        biencoder_params["path_to_model"] = args.biencoder_model
    biencoder = load_biencoder(biencoder_params)
    return biencoder, biencoder_params


################## rmq

def queue_doc_in_callback(ch, method, properties, body):
    print("[x] Received doc")
    body = json.loads(body.decode())

    @timeout_decorator.timeout(TIMEOUT)
    def timeout_encode_mention_from_doc(body):
        return encode_mention_from_doc(body)

    try:
        #doc = func_timeout(TIMEOUT, encode_mention_from_doc, args=(body))
        doc = timeout_encode_mention_from_doc(body)

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


def queue_entity_in_callback(ch, method, properties, body):
    print("[x] Received entity")
    res = encode_entity(body)
    ch.basic_publish(exchange='', routing_key=QUEUES['entity_out'], body=res)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def queue_mention_in_callback(ch, method, properties, body):
    print("[x] Received mention")
    res = encode_mention(body)
    ch.basic_publish(exchange='', routing_key=QUEUES['mention_out'], body=res)
    ch.basic_ack(delivery_tag=method.delivery_tag)

#################

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # biencoder
    parser.add_argument(
        "--biencoder_model",
        dest="biencoder_model",
        type=str,
        default="models/biencoder_wiki_large.bin",
        help="Path to the biencoder model.",
    )
    parser.add_argument(
        "--biencoder_config",
        dest="biencoder_config",
        type=str,
        default="models/biencoder_wiki_large.json",
        help="Path to the biencoder configuration.",
    )
    parser.add_argument(
        "--rabbiturl", type=str, default='amqp://guest:guest@rabbitmq:5672/', help="rabbitmq url",
    )
    parser.add_argument(
        "--queue", type=str, default="biencoder", help="rabbitmq queue root",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="timeout in seconds",
    )

    args = parser.parse_args()

    logger = logging.getLogger('biencoder_micros')

    print('Loading biencoder...')
    biencoder, biencoder_params = load_models(args)
    print('Device:', biencoder.device)
    print('Loading complete.')

    # RabbitMQ connection parameters
    RMQ_URL = args.rabbiturl
    QUEUE_ROOT = args.queue
    TIMEOUT = args.timeout

    QUEUES = {
        'doc_in': '{root}/doc/in',
        'doc_out': '{root}/doc/out',
        'mention_in': '{root}/mention/in',
        'mention_out': '{root}/mention/out',
        'entity_in': '{root}/entity/in',
        'entity_out': '{root}/entity/out',
        'errors': '{root}/errors'
    }
    
    for k in QUEUES:
        QUEUES[k] = QUEUES[k].format(root=QUEUE_ROOT)

    # Connect to RabbitMQ server
    connection = pika.BlockingConnection(pika.URLParameters(RMQ_URL))
    channel = connection.channel()


    channel.basic_qos(prefetch_count=1)

    channel.queue_declare(queue=QUEUES['doc_in'])
    channel.queue_declare(queue=QUEUES['mention_in'])
    channel.queue_declare(queue=QUEUES['entity_in'])

    channel.queue_declare(queue=QUEUES['doc_out'])
    channel.queue_declare(queue=QUEUES['mention_out'])
    channel.queue_declare(queue=QUEUES['entity_out'])

    channel.queue_declare(queue=QUEUES['errors'])

    # Set up the consumer
    channel.basic_consume(queue=QUEUES['doc_in'], on_message_callback=queue_doc_in_callback, auto_ack=False)
    channel.basic_consume(queue=QUEUES['mention_in'], on_message_callback=queue_mention_in_callback, auto_ack=False)
    channel.basic_consume(queue=QUEUES['entity_in'], on_message_callback=queue_entity_in_callback, auto_ack=False)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    # Start consuming messages
    channel.start_consuming()
