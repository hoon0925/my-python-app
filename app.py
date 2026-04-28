from flask import Flask, jsonify
import os
import socket
import time
import redis

app = Flask(__name__)

redis_host = os.getenv("REDIS_HOST", "redis-master.redis.svc.cluster.local")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_password = os.getenv("REDIS_PASSWORD", "redis-password-1234")

r = redis.Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
    decode_responses=True,
    socket_connect_timeout=2,
)


def slow_db_query(key):
    """느린 DB 쿼리 시뮬레이션"""
    time.sleep(2)
    return f"value-for-{key}"


@app.route("/")
def hello():
    return jsonify({
        "message": "Hello from CI/CD pipeline with Redis cache!",
        "version": os.getenv("APP_VERSION", "v2"),
        "hostname": socket.gethostname()
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/cache/<key>")
def get_cached(key):
    """cache-aside pattern"""
    start = time.time()

    try:
        cached = r.get(key)
    except redis.exceptions.RedisError as e:
        return jsonify({"error": f"Redis error: {e}"}), 500

    if cached:
        elapsed = time.time() - start
        return jsonify({
            "key": key,
            "value": cached,
            "source": "cache",
            "elapsed_seconds": round(elapsed, 3),
            "hostname": socket.gethostname()
        })

    value = slow_db_query(key)
    r.setex(key, 60, value)

    elapsed = time.time() - start
    return jsonify({
        "key": key,
        "value": value,
        "source": "db",
        "elapsed_seconds": round(elapsed, 3),
        "hostname": socket.gethostname()
    })


@app.route("/cache/<key>/clear", methods=["DELETE", "GET"])
def clear_cache(key):
    deleted = r.delete(key)
    return jsonify({"key": key, "deleted": deleted == 1})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
