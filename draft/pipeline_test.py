import pika

URL = 'amqp://guest:guest@127.0.0.1:5672/'

# Create a global channel variable to hold our channel object in
channel = None

# Step #2
def on_connected(connection):
    """Called when we are fully connected to RabbitMQ"""
    # Open a channel
    print('connect')
    connection.channel(on_open_callback=on_channel_open)

# Step #3
def on_channel_open(new_channel):
    """Called when our channel has opened"""
    global channel
    channel = new_channel
    print('channel opened')
    channel.queue_declare(queue="test", durable=True, exclusive=False, auto_delete=False, callback=on_queue_declared)

# Step #4
def on_queue_declared(frame):
    """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
    channel.basic_consume('test', handle_delivery)

# Step #5
def handle_delivery(channel, method, header, body):
    """Called when we receive a message from RabbitMQ"""
    print(body)

# Closing
def on_close(connection, exception):
    # Invoked when the connection is closed
    connection.ioloop.stop()

# Step #1: Connect to RabbitMQ using the default parameters
parameters = pika.URLParameters(URL)
connection = pika.SelectConnection(on_open_callback=on_connected, on_close_callback=on_close)

try:
    # Loop so we can communicate with RabbitMQ
    connection.ioloop.start()
except KeyboardInterrupt:
    # Gracefully close the connection
    connection.close()
    # Loop until we're fully closed.
    # The on_close callback is required to stop the io loop
    connection.ioloop.start()
