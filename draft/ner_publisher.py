import pika
from glob import glob
from tqdm import tqdm

src_path = '/home/rpozzi/chats_ner/*.json'

# RabbitMQ connection parameters
URL = 'amqp://guest:guest@127.0.0.1:5672/'
QUEUE_NAME = 'biencoder'

# Connect to RabbitMQ server
connection = pika.BlockingConnection(pika.URLParameters(URL))
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue=QUEUE_NAME)

# Send messages
for chat_file in tqdm(glob(src_path)):
    channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=chat_file)

# Close the connection
connection.close()
