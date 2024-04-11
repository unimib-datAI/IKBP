from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import requests
from gatenlp import Document
import yaml
import datetime
import os
import traceback
import pika

PIPELINEv = 'pipelineV2'

app = FastAPI()

config = {}

from dataclasses import dataclass

@dataclass
class PipeException(Exception):
    message: str = "This is a custom exception"

    def __str__(self):
        return f"{self.message}"

@app.post('/api/pipeline')
async def api_pipeline(doc: dict = Body(...), skip: bool | None = True):
    global config
    gDoc = Document.from_dict(doc)

    if PIPELINEv not in gDoc.features:
        gDoc.features[PIPELINEv] = {}
    gDoc.features[PIPELINEv]['pipeline'] = {
        'date': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S UTC"),
        'timestamp': datetime.datetime.utcnow().timestamp(),
        'result': 'pending',
    }
    print('>'*20, flush=True)
    for pipe in config['pipeline']:
        # TODO check if pipe already done ??
        # print(pipe['name'], skip, gDoc.features[PIPELINEv].get(pipe['name'], {}).get('result') == 'ok')
        if skip and gDoc.features[PIPELINEv].get(pipe['name'], {}).get('result') == 'ok':
            print('Skipping', pipe['name'], flush=True)
            gDoc.features[PIPELINEv][pipe['name']]['result'] = 'skipped'
            continue
        gDoc.features[PIPELINEv][pipe['name']] = {
            # 'name': pipe['name'],
            'url': pipe['url'],
            'date': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S UTC"),
            'timestamp': datetime.datetime.utcnow().timestamp(),
            'result': 'pending',
        }
        try:
            gDoc = call_pipe(pipe, gDoc)
        except PipeException as exc_obj:
            # TODO debug levels
            gDoc.features[PIPELINEv]['pipeline']['elapsed'] = datetime.datetime.utcnow().timestamp() - gDoc.features[PIPELINEv]['pipeline']['timestamp']
            pipeline_tb = ''.join(traceback.format_exception(exc_obj))
            print(pipeline_tb, flush=True)
            gDoc.features[PIPELINEv]['pipeline']['result'] = 'error'
            gDoc.features[PIPELINEv]['pipeline']['traceback'] = pipeline_tb
            print('x'*20, flush=True)
            return JSONResponse(
                status_code=500,
                content=gDoc.to_dict(),
            )

    gDoc.features[PIPELINEv]['pipeline']['elapsed'] = datetime.datetime.utcnow().timestamp() - gDoc.features[PIPELINEv]['pipeline']['timestamp']
    gDoc.features[PIPELINEv]['pipeline']['result'] = 'ok'
    print('<'*20, flush=True)
    return JSONResponse(
        status_code=200,
        content=gDoc.to_dict(),
    )

def call_pipe(pipe_config, gDoc):
    # TODO debug levels
    print('Calling', pipe_config['name'], flush=True)
    response = requests.post(pipe_config['url'], json=gDoc.to_dict())
    if not response.ok:
        raise PipeException(response.content)
    doc = response.json()
    doc['features'][PIPELINEv][pipe_config['name']]['elapsed'] = datetime.datetime.utcnow().timestamp() - doc['features'][PIPELINEv][pipe_config['name']]['timestamp']
    doc['features'][PIPELINEv][pipe_config['name']]['result'] = 'ok'
    return Document.from_dict(doc)

def load_config(config_path):
    global config
    with open(config_path, 'r') as fd:
        config = yaml.safe_load(fd)

def get_queue_broker_callback(outlist):
    if not isinstance(outlist, list):
        outlist = [outlist]
    def queue_doc_in_callback(ch, method, properties, body):
        try:
            for out in outlist:
                ch.basic_publish(exchange='', routing_key=out, body=body)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as exc_obj:
            print("Broker error!")
            pipeline_tb = ''.join(traceback.format_exception(exc_obj))
            print(pipeline_tb)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    return queue_doc_in_callback


def init_amqp():
    # RabbitMQ connection parameters
    global config
    RMQ_URL = os.environ.get('RABBITURL')

    # Connect to RabbitMQ server
    parameters = pika.URLParameters(RMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.queue_declare(queue=config['http_queue'], durable=True)

    for rule in config['amqp_rules']:
        rules_in = rule['in']
        if not isinstance(rules_in, list):
            rules_in = [rules_in]
        rules_out = rule['out']
        if not isinstance(rules_out, list):
            rules_out = [rules_out]

        for rin in rules_in:
            channel.queue_declare(queue=rin, durable=True)
        for rout in rules_out:
            channel.queue_declare(queue=rout, durable=True)

        for rin in rules_in:
            channel.basic_consume(queue=rin, on_message_callback=get_queue_broker_callback(rules_out), auto_ack=False)

        print('{name}: {in} --> {out}'.format(**rule))

    print(' [*] Waiting for messages. To exit press CTRL+C')
    # Start consuming messages
    return channel


load_config(os.environ.get('CONFIG_PATH', './config.yml'))

channel = init_amqp()
channel.start_consuming()

print('Started', flush=True)