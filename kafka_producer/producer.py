import praw
import json
import time
import os
import click
import multiprocessing
import concurrent.futures
from confluent_kafka import Producer
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")

# ✅ Set logging level
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# ✅ Retrieve values securely
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID")

# ✅ Kafka Configuration
conf = {
    'bootstrap.servers': KAFKA_BROKER,
}

logger.info(f"Kafka Broker: {KAFKA_BROKER}")
logger.info(f"Kafka Topic: {KAFKA_TOPIC}")

def wait_for_kafka(timeout=60, interval=5):
    """
    Wait until Kafka is reachable before creating the producer.
    - timeout: Total time to wait (seconds).
    - interval: Time between retries (seconds).
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # ✅ Try to create a temporary producer to check connection
            temp_producer = Producer(conf)
            temp_producer.list_topics(timeout=5)  # Check if broker responds
            logger.info("✅ Kafka is reachable!")
            return True
        except Exception as e:
            logger.info(f"❌ Waiting for Kafka... {e}")
            time.sleep(interval)
    
    logger.info("⛔ ERROR: Kafka is not reachable. Exiting.")
    exit(1)

# ✅ Wait for Kafka connection before initializing producer
wait_for_kafka()
producer = Producer(conf)
logger.info("🚀 Kafka Producer is ready!")


# ✅ Reddit API Configuration
logger.info("Initializing Reddit API...")
reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

logger.info("Reddit API initialized.")

# ✅ Default Values
DEFAULT_SUBREDDITS = ["cryptomoonshots", "memecoins", "solana", "ethereum"]
DEFAULT_POST_LIMIT = 500  # Number of posts per subreddit

def get_max_workers(subreddit_list):
    """Determine the optimal number of worker threads."""
    try:
        # Check if running inside a container (Kubernetes or Docker)
        if os.path.exists("/.dockerenv") or os.getenv("KUBERNETES_SERVICE_HOST"):
            return max(1, multiprocessing.cpu_count() // 2)  # Use half of available CPUs
        else:
            return max(1, os.cpu_count() or len(subreddit_list))  # Default to CPU count or list size
    except Exception:
        return len(subreddit_list)  # Default to list size


def delivery_report(err, msg):
    """Callback function to check if message was delivered successfully."""
    if err:
        logger.info(f"❌ Message failed delivery: {err}")
    else:
        logger.info(f"✅ Message delivered to {msg.topic()} [Partition {msg.partition()}]")

def convert_unix_to_utc(timestamp):
    """Convert Unix timestamp to UTC."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def fetch_and_send_posts(subreddit,post_limit):
    """Fetch latest posts from a single subreddit and send to Kafka."""
    logger.info(f"🚀 Fetching posts from r/{subreddit} (Limit: {post_limit})")

    # Fetch latest posts
    posts = reddit.subreddit(subreddit).new(limit=post_limit)

    # ✅ Send messages directly without checking duplicates
    for post in posts:
        reddit_data = {
            "id": post.id,
            "title": post.title,
            "upvotes": post.score,
            "num_comments": post.num_comments,
            "post_created_utc": convert_unix_to_utc(post.created_utc),
            "subreddit": post.subreddit.display_name,
            "selftext": post.selftext,
            "upvote_ratio": post.upvote_ratio,
            "kafka_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            producer.produce(
                topic=KAFKA_TOPIC,
                key=reddit_data["id"],
                value=json.dumps(reddit_data),
                callback=delivery_report
            )
            producer.poll(0)  # Poll events for message delivery callback
            logger.info(f"✅ Sent Post: {reddit_data['title']}")
        except Exception as e:
            logger.info(f"❌ Failed to send post: {e}")

    producer.flush()  # ✅ Ensure messages are sent before function exits
    logger.info(f"✅ Finished processing r/{subreddit}")


@click.command()
@click.option("--subreddits", default=",".join(DEFAULT_SUBREDDITS), help="Comma-separated list of subreddits")
@click.option("--limit", default=DEFAULT_POST_LIMIT, type=int, help="Number of posts per subreddit")
@click.option("--interval", default=5, type=int, help="Time interval between fetches (seconds)")
def fetch_reddit_posts(subreddits, limit, interval):
    """Parallel processing of multiple subreddits."""
    subreddit_list = subreddits.split(",")
    for subreddit in subreddit_list:
        fetch_and_send_posts(subreddit, limit)
        logger.info(f"⏳ Sleeping for {interval} seconds before next fetch...")
        time.sleep(interval)
    return True

if __name__ == "__main__":
    fetch_reddit_posts()

