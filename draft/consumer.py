import pika

# RabbitMQ connection parameters
URL = 'amqp://guest:guest@127.0.0.1:5672/'
QUEUE_NAME = 'hello'

# Callback function to handle received messages
def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)

# Connect to RabbitMQ server
connection = pika.BlockingConnection(pika.URLParameters(URL))
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue=QUEUE_NAME)

# Set up the consumer
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
# Start consuming messages
channel.start_consuming()
