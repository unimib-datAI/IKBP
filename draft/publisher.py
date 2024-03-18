import pika

# RabbitMQ connection parameters
URL = 'amqp://guest:guest@127.0.0.1:5672/'
QUEUE_NAME = 'hello'

# Connect to RabbitMQ server
connection = pika.BlockingConnection(pika.URLParameters(URL))
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue=QUEUE_NAME)

# Send messages
message = "Hello, Receiver!"
channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=message)
print(" [x] Sent %r" % message)

# Close the connection
connection.close()
