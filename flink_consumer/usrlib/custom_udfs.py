import json
import re
from pyflink.table import DataTypes
from pyflink.table.udf import ScalarFunction, udf


# The future transformer-based sentiment analysis udf
# is commented out because it requires a lot of memory
# and may not work on all machines.
# Uncomment it if you have enough memory and want to try it out.
#


# from transformers import TextClassificationPipeline, AutoModelForSequenceClassification, AutoTokenizer

# from transformers import AutoModelForSequenceClassification, AutoTokenizer
# import json

# class GetSentiment(ScalarFunction):
#     def __init__(self, model_name):
#         # Load the tokenizer and model
#         self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
#         self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
#         self.pipe = TextClassificationPipeline(model=self.model, tokenizer=self.tokenizer)

#     def eval(self, text):
#         if not text:
#             return json.dumps({"score": 0, "sentiment": "Neutral"})

#         predictions = self.pipe(text)


#         return json.dumps({
#             "score": predictions[0]["score"],
#             "sentiment": predictions[0]["label"]
#         })

# get_sentiment = udf(GetSentiment(), result_type=DataTypes.STRING())


from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class GetSentiment(ScalarFunction):
    """
    A UDF to get the sentiment of a text using the VADER Sentiment Analyzer
    """
    def open(self, function_context):
        self.analyzer = SentimentIntensityAnalyzer()

    def eval(self, text):
        if not text:
            return json.dumps(None)

        sentiment_score = self.analyzer.polarity_scores(text)["compound"]

        return json.dumps({
            "score": sentiment_score,
            "sentiment": "Positive" if sentiment_score > 0.2 else "Negative" if sentiment_score < -0.2 else "Neutral"
        })

get_sentiment = udf(GetSentiment(), result_type=DataTypes.STRING())



class ExtractCoin(ScalarFunction):
    """
    A UDF to extract the coin name from a text
    """
    def eval(self, text):
        if not text:
            return None

        # Regex pattern to find coins like "$CCC", "$DOGE", "$SHIBA"
        coin_pattern = r'\$[A-Za-z]{2,10}'
        matches = re.findall(coin_pattern, text)

        # Return first match or None
        return matches[0].upper() if matches else None

extract_coin = udf(ExtractCoin(), result_type=DataTypes.STRING())
