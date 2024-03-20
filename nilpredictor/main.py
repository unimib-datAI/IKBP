import pickle
import pandas as pd
from pydantic import BaseModel
from typing import List, Optional
import argparse
import textdistance
import statistics
from gatenlp import Document
import pika
import timeout_decorator
import traceback

# input: features
# output: NIL score

jaccardObj = textdistance.Jaccard(qval=None)
levenshteinObj = textdistance.Levenshtein(qval=None)

class Candidate(BaseModel):
    id: int
    indexer: int
    score: Optional[float]
    bi_score: Optional[float]

class Features(BaseModel):
    max_bi: Optional[float]
    max_cross: Optional[float]
    # text similarities
    title: Optional[str]
    mention: Optional[str]
    jaccard: Optional[float]
    levenshtein: Optional[float]
    # types
    mentionType: Optional[str]
    candidateType: Optional[str]
    candidateId: Optional[int]
    candidateIndexer: Optional[int]
    # stats
    topcandidates: Optional[List[Candidate]]
    secondiff: Optional[float]

def nilprediction_doc_api(doc: dict):
    doc = Document.from_dict(doc)

    annsets_to_link = set([doc.features.get('annsets_to_link', 'entities_merged')])

    input = []
    mentions = []

    for annset_name in set(doc.annset_names()).intersection(annsets_to_link):
        # if not annset_name.startswith('entities'):
        #     # considering only annotation sets of entities
        #     continue
        for mention in doc.annset(annset_name):
            if 'linking' in mention.features and mention.features['linking'].get('skip', False):
                # DATES should skip = true bcs linking useless
                continue
            gt_features = mention.features['linking']['top_candidate']
            feat = Features()
            if 'score' in gt_features:
                if 'score_bi' in gt_features:
                    # bi
                    feat.max_bi = gt_features['score_bi']
                    # cross
                    feat.max_cross = gt_features['score']
                else:
                    # bi only
                    feat.max_bi = gt_features['score']
            feat.mention = mention.features['mention'] if 'mention' in mention.features \
                                                        else doc.text[mention.start:mention.end]
            feat.title = gt_features['title'] if 'title' in gt_features else None

            feat.topcandidates = [Candidate(**c) for c in mention.features['additional_candidates']]

            input.append(feat)
            mentions.append(mention)

    nil_results = run(input)

    score_label = 'nil_score_cross' if 'nil_score_cross' in nil_results else 'nil_score_bi'
    add_score_bi = 'nil_score_cross' in nil_results

    for i, mention in enumerate(mentions):
        mention.features['linking']['nil_score'] = nil_results[score_label][i]
        mention.features['linking']['is_nil'] = bool(nil_results[score_label][i] < args.threshold)
        if add_score_bi:
            mention.features['linking']['nil_score_bi'] = nil_results[score_label][i]

        # delete title and url for nil
        if mention.features['linking']['is_nil']:
            mention.features['title'] = ""
            mention.features['url'] = ""
        # else:
        #     # add linking type now that we know it's not nil
        #     if mention.features['linking']['top_candidate'].get('type_'):
        #         mention.features['types'].append(mention.features['linking']['top_candidate']['type_'])
        #     mention.features['types'] = list(set(mention.features['types']))

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []
    doc.features['pipeline'].append('nilprediction')

    return doc.to_dict()

def nilprediction_api(input: List[Features]):
    return run(input)

def run(input: List[Features]):
    nil_X = pd.DataFrame()

    for i, features in enumerate(input):

        data = []
        index = []

        if features.max_bi:
            data.append(features.max_bi)
            index.append('max_bi')

        if features.max_cross:
            data.append(features.max_cross)
            index.append('max_cross')

        if features.secondiff:
            data.append(features.secondiff)
            index.append('secondiff')


        # process features
        _jacc, _leve = process_text_similarities(
            mention=features.mention, title=features.title, jaccard=features.jaccard, levenshtein=features.levenshtein)

        if _jacc is not None:
            data.append(_jacc)
            index.append('jaccard')

        if _leve is not None:
            data.append(_leve)
            index.append('levenshtein')

        # process types TODO

        # process stats TODO
        if features.topcandidates:
            # remove dummy candidates
            _topcandidates = [c for c in features.topcandidates if 'dummy' not in c]
            scores = [c.score for c in _topcandidates]

            stats = {
                'mean': statistics.mean(scores),
                'median': statistics.median(scores),
                'stdev': statistics.stdev(scores),
                'secondiff': scores[0] - scores[1]
            }

            assert scores[0] == max(scores)
            assert scores[1] == max(scores[1:])

            for i_,v in stats.items():
                data.append(v)
                index.append(i_)

        nil_X.loc[i, index] = pd.Series(data=data, index=index, name=i)

    # run the model
    result = {}

    if nil_bi_model is not None:
        result['nil_score_bi'] = list(map(lambda x: x[1], nil_bi_model.predict_proba(nil_X[nil_bi_features])))

    if nil_model is not None:
        result['nil_score_cross'] = list(map(lambda x: x[1], nil_model.predict_proba(nil_X[nil_features])))

    return result

def process_text_similarities(mention=None, title=None, jaccard=None, levenshtein=None):
    if jaccard is None:
        if not (title is None and mention is None):
            mention_ = mention.lower()
            title_ = title.lower()
            jaccard = jaccardObj.normalized_similarity(mention_, title_)
    if levenshtein is None:
        if not (title is None and mention is None):
            mention_ = mention.lower()
            title_ = title.lower()
            levenshtein = levenshteinObj.normalized_similarity(mention_, title_)

    return jaccard, levenshtein


def load_nil_models(args, logger=None):
    if logger:
        logger.info('Loading nil bi model')
    if args.nil_bi_model is not None:
        with open(args.nil_bi_model, 'rb') as fd:
            nil_bi_model = pickle.load(fd)

        nil_bi_features = args.nil_bi_features.split(',')
    else:
        nil_bi_model = None
        nil_bi_features = None

    if logger:
        logger.info('Loading nil bi model')
    if args.nil_model is not None:
        with open(args.nil_model, 'rb') as fd:
            nil_model = pickle.load(fd)

        nil_features = args.nil_features.split(',')
    else:
        nil_model = None
        nil_features = None

    return nil_bi_model, nil_bi_features, nil_model, nil_features

################## rmq

def queue_doc_in_callback(ch, method, properties, body):
    print("[x] Received doc")
    body = json.loads(body.decode())

    @timeout_decorator.timeout(TIMEOUT)
    def timeout_nilprediction_doc_api(body):
        return nilprediction_doc_api(body)

    try:
        doc = timeout_nilprediction_doc_api(body)

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
        "--nil-bi-model", type=str, default=None, help="path to nil bi model",
    )

    parser.add_argument(
        "--nil-bi-features", type=str, default=None, help="features of the nil bi model (comma separated)",
    )

    parser.add_argument(
        "--nil-model", type=str, default=None, help="path to nil model",
    )

    parser.add_argument(
        "--nil-features", type=str, default=None, help="features of the nil model (comma separated)",
    )

    parser.add_argument(
        "--threshold", type=float, default="0.5", help="threshold below which mention is nil",
    )
    parser.add_argument(
        "--rabbiturl", type=str, default='amqp://guest:guest@rabbitmq:5672/', help="rabbitmq url",
    )
    parser.add_argument(
        "--queue", type=str, default="nilpred", help="rabbitmq queue root",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="timeout in seconds",
    )

    args = parser.parse_args()

    print('Loading nil models...')
    nil_bi_model, nil_bi_features, nil_model, nil_features = load_nil_models(args)
    print('Loading complete.')

    # RabbitMQ connection parameters
    RMQ_URL = args.rabbiturl
    QUEUE_ROOT = args.queue
    TIMEOUT = args.timeout

    QUEUES = {
        'doc_in': '{root}/doc/in',
        'doc_out': '{root}/doc/out',
        'list_in': '{root}/list/in',
        'list_out': '{root}/list/out',
        'errors': '{root}/errors'
    }
    
    for k in QUEUES:
        QUEUES[k] = QUEUES[k].format(root=QUEUE_ROOT)

    # Connect to RabbitMQ server
    connection = pika.BlockingConnection(pika.URLParameters(RMQ_URL))
    channel = connection.channel()


    channel.basic_qos(prefetch_count=1)

    channel.queue_declare(queue=QUEUES['doc_in'])
    channel.queue_declare(queue=QUEUES['list_in'])

    channel.queue_declare(queue=QUEUES['doc_out'])
    channel.queue_declare(queue=QUEUES['list_out'])

    channel.queue_declare(queue=QUEUES['errors'])

    # Set up the consumer
    channel.basic_consume(queue=QUEUES['doc_in'], on_message_callback=queue_doc_in_callback, auto_ack=False)
    # channel.basic_consume(queue=QUEUES['list_in'], on_message_callback=queue_list_in_callback, auto_ack=False)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    # Start consuming messages
    channel.start_consuming()