import pika
import requests
import json
import sys
from pathlib import Path
import os
import time

dest_queue = 'indexer'
dest_path = Path('linked')

# RabbitMQ connection parameters
URL = 'amqp://guest:guest@127.0.0.1:5672/'
QUEUE_NAME = 'biencoder'

NEL_URL = 'http://10.0.0.113:10880/api/blink/biencoder/mention/doc'

# Callback function to handle received messages
# def callback(ch, method, properties, body):
#     src_path = body.decode()
#     print(" [x] Received", src_path)
#     with open(src_path, 'r') as fd:
#         doc = json.load(fd)
#     res = requests.post(NEL_URL, json = doc)
#     new_doc = res.json()
#     dest_file_name = str(dest_path / os.path.basename(src_path))
#     if res.ok:
#         with open(dest_file_name, 'w') as fd:
#             json.dump(new_doc, fd)
#         ch.basic_publish(exchange='', routing_key=dest_queue, body=dest_file_name)
#     else:
#         raise Exception('ec')
#         dest_file_name += '.error'
#         with open(dest_file_name, 'w') as fd:
#             fd.write(str(res.content))

# Connect to RabbitMQ server

connection = None
channel = None


def connect():
    global connection
    global channel
    global URL
    global QUEUE_NAME

    connection = pika.BlockingConnection(pika.URLParameters(URL))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    
    # Declare the queue
    channel.queue_declare(queue=QUEUE_NAME)
    
    # Set up the consumer
    # channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

def main():
    global connection
    global channel
    global URL
    global QUEUE_NAME
    global dest_queue
    global dest_path
    global NEL_URL

    for method, properties, body in channel.consume(QUEUE_NAME):
        src_path = body.decode()
        print(" [x] Received", src_path)
        channel.basic_ack(method.delivery_tag)
        with open(src_path, 'r') as fd:
            doc = json.load(fd)
        res = requests.post(NEL_URL, json = doc)
        new_doc = res.json()
        dest_file_name = str(dest_path / os.path.basename(src_path))
        try:
            if res.ok:
                with open(dest_file_name, 'w') as fd:
                    json.dump(new_doc, fd)
                #channel.basic_ack(method.delivery_tag)
                channel.basic_publish(exchange='', routing_key=dest_queue, body=dest_file_name)
            else:
                dest_file_name += '.error'
                with open(dest_file_name, 'w') as fd:
                    fd.write(str(res.content))
                #channel.basic_nack(method.delivery_tag)
        except:
            dest_file_name += '.error'
            with open(dest_file_name, 'w') as fd:
                fd.write(str(res.content))

connect()

main()

