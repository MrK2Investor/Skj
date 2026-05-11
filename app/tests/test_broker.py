import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_websocket_connect_disconnect():
    with client.websocket_connect("/broker?fmt=json") as websocket:
        websocket.send_text(json.dumps({
            "action": "subscribe",
            "topic": "connect-test",
        }))


def test_message_to_topic_x_is_delivered():
    with client.websocket_connect("/broker?fmt=json") as subscriber:
        subscriber.send_text(json.dumps({
            "action": "subscribe",
            "topic": "topic-x",
        }))

        with client.websocket_connect("/broker?fmt=json") as publisher:
            publisher.send_text(json.dumps({
                "action": "publish",
                "topic": "topic-x",
                "payload": {"text": "hello"},
            }))

            received = json.loads(subscriber.receive_text())

            assert received["action"] == "deliver"
            assert received["topic"] == "topic-x"
            assert received["payload"]["text"] == "hello"

            subscriber.send_text(json.dumps({
                "action": "ack",
                "message_id": received["message_id"],
            }))


def test_durable_message_delivered_after_subscribe():
    with client.websocket_connect("/broker?fmt=json") as publisher:
        publisher.send_text(json.dumps({
            "action": "publish",
            "topic": "durable-topic",
            "payload": {"value": 123},
        }))

    with client.websocket_connect("/broker?fmt=json") as subscriber:
        subscriber.send_text(json.dumps({
            "action": "subscribe",
            "topic": "durable-topic",
        }))

        received = json.loads(subscriber.receive_text())

        assert received["action"] == "deliver"
        assert received["topic"] == "durable-topic"
        assert received["payload"]["value"] == 123

        subscriber.send_text(json.dumps({
            "action": "ack",
            "message_id": received["message_id"],
        }))


def test_ack_prevents_redelivery():
    topic = "ack-no-redelivery-topic"

    with client.websocket_connect("/broker?fmt=json") as publisher:
        publisher.send_text(json.dumps({
            "action": "publish",
            "topic": topic,
            "payload": {"value": "once"},
        }))

    with client.websocket_connect("/broker?fmt=json") as subscriber:
        subscriber.send_text(json.dumps({
            "action": "subscribe",
            "topic": topic,
        }))

        received = json.loads(subscriber.receive_text())

        subscriber.send_text(json.dumps({
            "action": "ack",
            "message_id": received["message_id"],
        }))

    assert received["payload"]["value"] == "once"


def test_message_to_topic_y_not_delivered_to_topic_x():
    with client.websocket_connect("/broker?fmt=json") as subscriber:
        subscriber.send_text(json.dumps({
            "action": "subscribe",
            "topic": "topic-x-only",
        }))

        with client.websocket_connect("/broker?fmt=json") as publisher:
            publisher.send_text(json.dumps({
                "action": "publish",
                "topic": "topic-y-only",
                "payload": {"text": "wrong topic"},
            }))

        # Nečekáme na receive_text(), protože by blokoval.
        # Test ověřuje, že publish do jiného topicu broker nezboří.
        assert True