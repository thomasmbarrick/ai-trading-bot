from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Tuple

# Set the device to GPU if available, otherwise use CPU.
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load the tokenizer and model for sentiment analysis using FinBERT from the Hugging Face model hub.
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").to(device)

# Define sentiment labels corresponding to the output classes of the model.
labels = ["positive", "negative", "neutral"]

def estimate_sentiment(news: str) -> Tuple[float, str]:

    # Ensure the input text is a string
    if not isinstance(news, str):
        raise ValueError("Input must be a string.")

    # Tokenize the input news text and prepare tensors for the model
    tokens = tokenizer(news, return_tensors="pt", padding=True, truncation=True).to(device)

    # Perform a forward pass through the model to get the logits (raw predictions)
    with torch.no_grad():  # Disable gradient calculation for inference to save memory and computation
        outputs = model(**tokens)

    # Get logits from model outputs
    logits = outputs["logits"]

    # Apply softmax to the logits to get probabilities
    probabilities = torch.nn.functional.softmax(logits, dim=-1)

    # Determine the index of the highest probability
    max_index = torch.argmax(probabilities, dim=-1).item()

    # Extract the probability and sentiment label
    probability = probabilities[0, max_index].item()
    sentiment = labels[max_index]

    return probability, sentiment
 