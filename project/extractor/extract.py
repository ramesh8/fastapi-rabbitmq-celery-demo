import datetime
import json
from dotenv import load_dotenv
import openai
import os
from pymongo import MongoClient


# @rate_limit()
def extract_from_openai(ocr_text):

    mongo = MongoClient("mongodb://mongodbserver:27017/")
    db = mongo["asyncdemo"]
    db_prompts = db["mq_openai_prompts"]
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_KEY")

    # Create a prompt for GPT-3.5-turbo
    prompt = f"""Detect Invoices from following text and Extract entities named invoice_number,invoice_date,invoice_amount,vendor_name,vendor_address,vendor_city,vendor_zipcode and give me all the line items if present for each invoice and arrange them by invoice_number in json format.
    Text: {ocr_text}
    Entities:"""

    db_prompts.insert_one({"prompt": prompt, "timestamp": datetime.datetime.utcnow()})

    # Make an API call to OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    # Access the generated content from the first choice
    generated_content = response["choices"][0]["message"]["content"]
    outputjson = generated_content.replace("```json", "").replace("```", "")

    output = json.loads(outputjson)
    return output
