import pika
import requests
import json
import sys
from pathlib import Path
import os

dest_queue = 'nilpred'
dest_path = Path('indexed')

# RabbitMQ connection parameters
URL = 'amqp://guest:guest@127.0.0.1:5672/'
QUEUE_NAME = 'indexer'

API_URL = 'http://10.0.0.113:10880/api/indexer/search/doc'

# Callback function to handle received messages
def callback(ch, method, properties, body):
    print(" [x] Received")
    src_path = body.decode()
    with open(src_path, 'r') as fd:
        doc = json.load(fd)
    res = requests.post(API_URL, json = doc)
    new_doc = res.json()
    dest_file_name = str(dest_path / os.path.basename(src_path))
    if res.ok:
        with open(dest_file_name, 'w') as fd:
            json.dump(new_doc, fd)
        ch.basic_publish(exchange='', routing_key=dest_queue, body=dest_file_name)
        ch.basic_ack(method.delivery_tag)
    else:
        dest_file_name += '.error'
        with open(dest_file_name, 'w') as fd:
            fd.write(str(res.content))
        ch.basic_nack(method.delivery_tag)

# Connect to RabbitMQ server
connection = pika.BlockingConnection(pika.URLParameters(URL))
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue=QUEUE_NAME)

print(' [*] Waiting for messages. To exit press CTRL+C')
for method, properties, body in channel.consume(QUEUE_NAME):
    callback(channel, method, properties, body)
