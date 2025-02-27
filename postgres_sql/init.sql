-- Ensure the database 'reddit' exists
CREATE DATABASE reddit;

CREATE DATABASE airflow;

-- Connect to the reddit database
\c reddit;

-- Create the reddit_posts table if it does not exist
CREATE TABLE IF NOT EXISTS reddit_posts (
    id TEXT PRIMARY KEY,
    title TEXT,
    upvotes INT,
    num_comments INT,
    post_created_utc TIMESTAMP,
    subreddit TEXT,
    selftext TEXT,
    upvote_ratio FLOAT,
    kafka_timestamp TIMESTAMP,
    postgres_timestamp TIMESTAMP,
    time_to_process INT,
    coin_name TEXT,
    sentiment TEXT
);

# Set the local time zone to UTC
SET table.local-time-zone = 'UTC';
