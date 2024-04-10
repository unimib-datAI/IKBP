import argparse
import re
from gatenlp import Document
from utils import make_clusters
import pickle
import json
import pika
import watchdog
import traceback

def queue_doc_in_callback(ch, method, properties, body):
    print("[x] Received doc")
    body = json.loads(body.decode())

    # watchdog
    # TODO better to not start the watchdog thread at every message.
    # the thread should stay alive
    wtd = watchdog.WatchdogThread(
        timeout = TIMEOUT,
        memory = MAX_MEM,
        gpu = 100, # dummy
    )

    wtd.set_handler()

    try:
        #doc = func_timeout(TIMEOUT, encode_mention_from_doc, args=(body))
        wtd.start()
        doc = make_clusters(body, model)
        doc = doc.to_dict()

        ch.basic_publish(exchange='', routing_key=QUEUES['doc_out'], body=json.dumps(doc))
        ch.basic_ack(delivery_tag=method.delivery_tag)

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
        "--model", type=str, default="/home/app/models/clustering/xgb_clustering.sav", help="model path",
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
    parser.add_argument(
        "--max_memory", type=int, default=1000000, help="max memory in bytes",
    )

    args = parser.parse_args()
    
    print('Loading model...')
    model = pickle.load(open(args.model, 'rb'))
    print('Model loaded.')

    # RabbitMQ connection parameters
    RMQ_URL = args.rabbiturl
    QUEUE_ROOT = args.queue
    TIMEOUT = args.timeout
    MAX_MEM = args.max_memory

    QUEUES = {
        'doc_in': '{root}/doc/in',
        'doc_out': '{root}/doc/out',
        'errors': '{root}/errors'
    }

    # Connect to RabbitMQ server
    parameters = pika.URLParameters(RMQ_URL)
    parameters.heartbeat = TIMEOUT + 1
    parameters.blocked_connection_timeout = TIMEOUT + 1
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()


    channel.basic_qos(prefetch_count=1)

    for k in QUEUES:
        QUEUES[k] = QUEUES[k].format(root=QUEUE_ROOT)
        channel.queue_declare(queue=QUEUES[k])

    # Set up the consumer
    channel.basic_consume(queue=QUEUES['doc_in'], on_message_callback=queue_doc_in_callback, auto_ack=False)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    # Start consuming messages
    channel.start_consuming()