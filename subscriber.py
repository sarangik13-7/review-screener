# subscriber.py
import os
import json
from google.cloud import pubsub_v1

credentials_path = r"xxx.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

subscription_path = "projects/qwerty-dev/subscriptions/Reviews-sub"

def callback(message):
    """
    Callback function to handle incoming Pub/Sub messages.

    Args:
        message (pubsub_v1.subscriber.message.Message): The message received from Pub/Sub.
    """
    non_compliant_reviews = json.loads(message.data.decode("utf-8"))
    print(f" [x] Received {non_compliant_reviews}")
    # Process the non-compliant reviews here
    # For example, save to a file or a database
    with open("non_compliant_reviews_output.json", "a") as fp:
        json.dump(non_compliant_reviews, fp, indent=4)
        fp.write('\n')
    
    message.ack()

def main():
    """
    Main function to set up the Pub/Sub subscriber and start listening for messages.
    """
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path("cdnassets", "Reviews-sub")

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print("Listening for messages on {}...".format(subscription_path))

    with subscriber:
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            streaming_pull_future.result()

if __name__ == "__main__":
    main()
