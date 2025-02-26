from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import EnvironmentSettings, StreamTableEnvironment
import re

from threading import Timer
import logging
import os
import dotenv
from custom_udfs import get_sentiment, extract_coin

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Load environment variables from .env file
dotenv.load_dotenv(dotenv_path=".env")

KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID")
KAFKA_SOURCE_TABLE = os.getenv("KAFKA_SOURCE_TABLE")
POSTGRES_URL = os.getenv("POSTGRES_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
REDDIT_DATABASE = os.getenv("REDDIT_DATABASE")
REDDIT_POSTS_TABLE = os.getenv("REDDIT_POSTS_TABLE")
FLINK_AUTO_OFFSET = os.getenv("FLINK_AUTO_OFFSET", "earliest")
FLINK_SCAN_STARTUP_MODE = os.getenv("FLINK_SCAN_STARTUP_MODE", "earliest-offset")


# 💡 Create Kafka Source Table
def create_reddit_source_kafka(t_env):
    """
    Create a Kafka source table to read data from the Kafka topic
    :param t_env: Table Environment
    :return: Kafka Source Table
    """
    source_ddl = f"""
        CREATE TABLE {KAFKA_SOURCE_TABLE} (
            id VARCHAR,
            title VARCHAR,
            upvotes INT,
            num_comments INT,
            post_created_utc TIMESTAMP,
            subreddit VARCHAR,
            selftext VARCHAR,
            upvote_ratio FLOAT,
            kafka_timestamp TIMESTAMP
        ) WITH (
            'connector' = 'kafka',
            'properties.bootstrap.servers' = '{KAFKA_BROKER}',
            'topic' = '{KAFKA_TOPIC}',
            'properties.group.id' = '{KAFKA_GROUP_ID}',
            'properties.auto.offset.reset' = '{FLINK_AUTO_OFFSET}',
            'scan.startup.mode' = '{FLINK_SCAN_STARTUP_MODE}',
            'format' = 'json'
        );
    """
    t_env.execute_sql(source_ddl)
    return KAFKA_SOURCE_TABLE


# 💡 Create PostgreSQL Sink Table using JDBC
def create_reddit_sink_postgres(t_env):
    """
    Create a PostgreSQL sink table to write data to the PostgreSQL database
    :param t_env: Table Environment
    :return: PostgreSQL Sink Table
    """
    sink_ddl = f"""
        CREATE TABLE {REDDIT_POSTS_TABLE} (
            id VARCHAR PRIMARY KEY,
            title VARCHAR,
            upvotes INT,
            num_comments INT,
            post_created_utc TIMESTAMP,
            subreddit VARCHAR,
            selftext VARCHAR,
            upvote_ratio FLOAT,
            kafka_timestamp TIMESTAMP,
            postgres_timestamp TIMESTAMP,
            time_to_process INT,
            coin_name VARCHAR,
            sentiment VARCHAR
        ) WITH (
            'connector' = 'jdbc',
            'url' = '{POSTGRES_URL}',
            'table-name' = '{REDDIT_POSTS_TABLE}',
            'username' = '{POSTGRES_USER}',
            'password' = '{POSTGRES_PASSWORD}',
            'driver' = 'org.postgresql.Driver'
        );
    """
    t_env.execute_sql(sink_ddl)
    return REDDIT_POSTS_TABLE


# 🚀 Main Flink Streaming Job
def flink_job():
    """
    Main Flink Job to read data from Kafka, process it, and write it to PostgreSQL
    """
    
    logger.info('✅ Starting Job!')

    # Set up the execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    logger.info('✅ Got streaming environment')
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(int(os.environ.get("FLINK_PARALLELISM", 1)))

    # Set up the table environment
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    # Register Sentiment Analysis UDF
    t_env.create_temporary_function("get_sentiment", get_sentiment)
    t_env.create_temporary_function("extract_coin", extract_coin)

    try:
        logger.info("✅ Creating Kafka Source Table...")
        reddit_source = create_reddit_source_kafka(t_env)
        logger.info(f"✔ Created Source Table: {reddit_source}")

        logger.info("✅ Creating PostgreSQL Sink Table...")
        postgres_sink = create_reddit_sink_postgres(t_env)
        logger.info(f"✔ Created PostgreSQL Sink Table: {postgres_sink}")

        logger.info('✅ Inserting Data into PostgreSQL...')
        result = t_env.execute_sql(
            f"""
            INSERT INTO {postgres_sink}
            SELECT 
                id, 
                title,
                upvotes,
                num_comments,
                post_created_utc,
                subreddit,
                selftext,
                upvote_ratio,
                kafka_timestamp,
                CURRENT_TIMESTAMP as postgres_timestamp,
                0 as time_to_process,
                extract_coin(title || ' ' || selftext) AS coin_name,
                get_sentiment(title || ' ' || selftext) AS sentiment
            FROM {reddit_source};
            """
        )
        result.wait()
        # Execute the SQL query and retrieve the result as a Table
        logger.info("✅ Data inserted successfully!")
    except Exception as e:
        logger.error("❌ Writing records from Kafka to PostgreSQL failed:", str(e))


# 🚀 Run the Flink Job
if __name__ == '__main__':
    flink_job()
