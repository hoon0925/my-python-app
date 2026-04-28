from flask import Flask, jsonify, request
import os
import socket
import time
import json
import redis
import pika

app = Flask(__name__)

# Redis (이전 cache-aside)
redis_host = os.getenv("REDIS_HOST", "redis-master.redis.svc.cluster.local")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_password = os.getenv("REDIS_PASSWORD", "redis-password-1234")

r = redis.Redis(
    host=redis_host, port=redis_port, password=redis_password,
    decode_responses=True, socket_connect_timeout=2,
)

# RabbitMQ
rabbit_host = os.getenv("RABBIT_HOST", "rabbitmq.rabbitmq.svc.cluster.local")
rabbit_user = os.getenv("RABBIT_USER", "admin")
rabbit_password = os.getenv("RABBIT_PASSWORD", "rabbit-password-1234")
rabbit_queue = os.getenv("RABBIT_QUEUE", "tasks")


def get_rabbit_connection():
    creds = pika.PlainCredentials(rabbit_user, rabbit_password)
    return pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbit_host, credentials=creds)
    )


def slow_db_query(key):
    time.sleep(2)
    return f"value-for-{key}"


@app.route("/")
def hello():
    return jsonify({
        "message": "Hello from CI/CD pipeline with Redis + RabbitMQ!",
        "version": os.getenv("APP_VERSION", "v3"),
        "hostname": socket.gethostname()
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/cache/<key>")
def get_cached(key):
    start = time.time()
    try:
        cached = r.get(key)
    except redis.exceptions.RedisError as e:
        return jsonify({"error": f"Redis error: {e}"}), 500

    if cached:
        return jsonify({
            "key": key, "value": cached, "source": "cache",
            "elapsed_seconds": round(time.time() - start, 3),
            "hostname": socket.gethostname()
        })

    value = slow_db_query(key)
    r.setex(key, 60, value)
    return jsonify({
        "key": key, "value": value, "source": "db",
        "elapsed_seconds": round(time.time() - start, 3),
        "hostname": socket.gethostname()
    })


@app.route("/publish", methods=["POST"])
def publish():
    """메시지를 RabbitMQ에 발행 (Producer)"""
    data = request.get_json() or {}
    message = data.get("message", "default-message")

    try:
        conn = get_rabbit_connection()
        channel = conn.channel()
        channel.queue_declare(queue=rabbit_queue, durable=True)

        body = json.dumps({
            "message": message,
            "published_by": socket.gethostname(),
            "timestamp": time.time(),
        })

        channel.basic_publish(
            exchange="",
            routing_key=rabbit_queue,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2),  # 영속 메시지
        )
        conn.close()

        return jsonify({
            "status": "published",
            "queue": rabbit_queue,
            "message": message,
            "publisher": socket.gethostname()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
