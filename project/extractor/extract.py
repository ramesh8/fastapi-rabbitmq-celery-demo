from dotenv import load_dotenv
import openai
import os


def extract_from_openai(ocr_text):
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_KEY")

    # Create a prompt for GPT-3.5-turbo
    prompt = f"""Extract entities named invoice_number,invoice_date,invoice_amount,vendor_name,vendor_address,vendor_city,vendor_zipcode and give me all the line items if present from the provided text, and arrange them in json format.
    Text: {ocr_text}
    Entities:"""

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

    return generated_content
