import ssl, pika
import asyncio
import websockets

def test_distant_connection():
    ssl_context = ssl.create_default_context()
    # ssl_context.check_hostname = False
    # ssl_context.verify_mode = ssl.CERT_NONE

    params = pika.ConnectionParameters(
        host='amqp.verdelia.com',
        port=5671,
        virtual_host='/',  # or your custom vhost
        ssl_options=pika.SSLOptions(ssl_context, server_hostname='amqp.verdelia.com'),
        credentials=pika.PlainCredentials('prod_user', 'NewStrongPassword123!')
    )

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue='test')
    channel.basic_publish(exchange='', routing_key='test', body='Hello')
    print("Message sent successfully!")
    connection.close()

def test_local_connection():

    params = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        virtual_host='/verdelia',  # or your custom vhost
        credentials=pika.PlainCredentials('dev_user', 'dev_pass')
    )

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue='test')
    channel.basic_publish(exchange='', routing_key='test', body='Hello')
    print("Message sent successfully!")
    connection.close()


def listen_local_connection():

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
        host='localhost',
        port=5672,
        virtual_host='/verdelia',  # or your custom vhost
        credentials=pika.PlainCredentials('dev_user', 'dev_pass')
    )
    )
    channel = connection.channel()

    # 1. Exchange
    channel.exchange_declare(
        exchange='user_notifications',
        exchange_type='direct',
        durable=True
    )

    # 2. Queue
    queue_name = "user.4"
    channel.queue_declare(queue=queue_name, durable=True)

    # 3. Bind queue to exchange
    channel.queue_bind(
        exchange='user_notifications',
        queue=queue_name,
        routing_key="user.4"
    )

    # 4. Callback
    def callback(ch, method, properties, body):
        print(f"[✔] Received message on {method.routing_key}: {body.decode()}")
        ch.basic_ack(method.delivery_tag)

    # 5. Consume
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print(f"[*] Listening on {queue_name}...")
    channel.start_consuming()


def pass_gen():
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    password = ''.join(secrets.choice(alphabet) for _ in range(24))
    print(password)



async def test_ws():
    WS_URL = "wss://verdelia.com/stream/ws/2"   
    try:
        print(f"Connecting to {WS_URL}...")
        async with websockets.connect(WS_URL) as websocket:
            while(True):
                print("Connected!")

                # Send a message
                # await websocket.send("Hello WebSocket Server!")
                # print("Message sent.")

                # Wait for a response
                response = await websocket.recv()
                print("Received:", response)

    except Exception as e:
        print("Error:", e)




# asyncio.run(test_ws())


listen_local_connection()
# pass_gen()