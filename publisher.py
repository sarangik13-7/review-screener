# publisher.py
import json
import os
import requests
from google.cloud import pubsub_v1
from concurrent.futures import ThreadPoolExecutor, as_completed

credentials_path = r"xxx.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

topic_path = "projects/qwerty-dev/topics/Reviews"
publisher = pubsub_v1.PublisherClient()

sku_list = []
api_url = ""

def publish_message(message, topic_path):
    """
    Publish a message to a Pub/Sub topic.

    Args:
        message (dict): The message to be published.
        topic_path (str): The Pub/Sub topic path.

    Returns:
        str: The ID of the published message.
    """
    message_json = json.dumps(message).encode("utf-8")
    future = publisher.publish(topic_path, data=message_json)
    print(f" [x] Sent {message}")
    return future.result()

def call_flask_api(sku_list, api_url):
    """
    Call the Flask API to process reviews for a list of SKUs.

    Args:
        sku_list (list): The list of SKU codes.
        api_url (str): The URL of the Flask API endpoint.

    Returns:
        dict: The non-compliant reviews returned by the Flask API.
    """
    response = requests.post(api_url, json={"sku_list": sku_list})
    return response.json()

if __name__ == "__main__":
    # Call the Flask API to process reviews
    non_compliant_reviews = call_flask_api(sku_list, api_url)

    # Publish non-compliant reviews to the Pub/Sub topic
    if non_compliant_reviews:
        publish_message(non_compliant_reviews, topic_path)
