from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import cohere

import os
import csv



app = Flask(__name__)
api_key = "ENTER_YOUR_COHERE_API_KEY"

headers = {
    "User-Agent": "...",
    "Accept": "...",
}


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/input", methods=["POST"])
def input():
    url = request.form.get("url")
    if not url:
        return render_template("index.html", error="Please enter a valid URL.")

    try:
        html = requests.get(url, headers=headers).text
        soup = BeautifulSoup(html, "html.parser")
        visible_text = soup.get_text()

        co = cohere.Client(api_key)

        prompt = f"""
            You are a professional e-commerce data extractor.

            Your task is to extract structured product information from the following page text. The page may contain multiple products from different categories (e.g., electronics, fashion, appliances, etc.).

            Extract each product individually and include only relevant product details. Do not include ads, recommendations, or unrelated content.

            For each product, extract the following fields (fill only if available):
            - Title
            - Brand
            - Category
            - Price (in INR)
            - Rating (out of 5)
            - Discount (if any)
            - Warranty (if mentioned)
            - Key Features (bullet points or short summary)
            - Specifications (if available)

            **Format strictly like this:**
            Title: ...
            Brand: ...
            Category: ...
            Price: ...
            Rating: ...
            Discount: ...
            Warranty: ...
            Key Features: ...
            Specifications: ...

            Separate each product block with a line containing only: ---
            Use English language only.
            Do not guess missing data — leave fields blank if not available.
            Ensure each product block is complete and clearly separated.

            Here is the page text:
            {visible_text}
            """



        response = co.generate(
            model="command-r-plus",
            prompt=prompt,
            max_tokens=1000
        )

        ai_output = response.generations[0].text
        data_list = parse_ai_output(ai_output)

        fieldnames = set()
        for item in data_list:
            fieldnames.update(item.keys())
        fieldnames = list(fieldnames)

        with open("product_info.csv", "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_list)

        return render_template("index.html", data=data_list, download_link="/download")

    except Exception as e:
        return render_template("index.html", error=f"Error: {str(e)}")

@app.route("/download")
def download():
    return send_file("product_info.csv", as_attachment=True)

def parse_ai_output(ai_output):
    product_blocks = ai_output.split("---")
    all_data = []

    for block in product_blocks:
        lines = block.strip().split("\n")
        product_data = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                product_data[key.strip().lower()] = value.strip()
        if product_data:  # Avoid empty dicts
            all_data.append(product_data)

    return all_data


if __name__ == "__main__":
    app.run(debug=True)