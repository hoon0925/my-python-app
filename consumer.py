"""RabbitMQ Consumer - 별도 Pod으로 백그라운드 실행"""
import os
import json
import time
import socket
import pika

rabbit_host = os.getenv("RABBIT_HOST", "rabbitmq.rabbitmq.svc.cluster.local")
rabbit_user = os.getenv("RABBIT_USER", "admin")
rabbit_password = os.getenv("RABBIT_PASSWORD", "rabbit-password-1234")
rabbit_queue = os.getenv("RABBIT_QUEUE", "tasks")


def callback(ch, method, properties, body):
    """메시지 수신 콜백"""
    try:
        data = json.loads(body)
        print(f"[{socket.gethostname()}] Received: {data}", flush=True)
        # 실제 처리 시뮬레이션 (1초 작업)
        time.sleep(1)
        print(f"[{socket.gethostname()}] Processed: {data['message']}", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    print(f"Consumer starting on {socket.gethostname()}...", flush=True)
    while True:
        try:
            creds = pika.PlainCredentials(rabbit_user, rabbit_password)
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbit_host, credentials=creds)
            )
            channel = conn.channel()
            channel.queue_declare(queue=rabbit_queue, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=rabbit_queue, on_message_callback=callback)

            print(f"[{socket.gethostname()}] Waiting for messages...", flush=True)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection error: {e}, retrying in 5s...", flush=True)
            time.sleep(5)
        except KeyboardInterrupt:
            print("Stopping consumer", flush=True)
            break


if __name__ == "__main__":
    main()
