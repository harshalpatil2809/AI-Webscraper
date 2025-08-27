from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import cohere
import csv
import io


app = Flask(__name__, static_folder="static", template_folder="templates")
api_key = "P29W8J4bK20sBAAh7OtHxazwLg5l2vQ7EoVL6A26"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
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
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return render_template("index.html", error=f"Failed to fetch page. Status code: {response.status_code}")
        html = response.text
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
        print("AI Output:", ai_output)  

        data_list = parse_ai_output(ai_output)
        print("Parsed Data:", data_list)  

        fieldnames = set()
        for item in data_list:
            fieldnames.update(item.keys())
        fieldnames = list(fieldnames)

        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_list)
        csv_data = output.getvalue()
        output.close()

        return render_template("index.html", data=data_list, csv_data=csv_data)

    except Exception as e:
        print("Error:", str(e))  
        return render_template("index.html", error=f"Error: {str(e)}")

@app.route("/download", methods=["POST"])
def download():
    csv_data = request.form.get("csv_data")
    if not csv_data:
        return "No CSV data found", 400

    return send_file(
        io.BytesIO(csv_data.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="product_info.csv"
    )

def parse_ai_output(ai_output):
    expected_fields = [
        "Title", "Brand", "Category", "Price", "Rating", "Discount",
        "Warranty", "Key Features", "Specifications"
    ]
    product_blocks = ai_output.split("---")
    all_data = []

    for block in product_blocks:
        lines = block.strip().split("\n")
        product_data = {field: "" for field in expected_fields}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                if key in expected_fields:
                    product_data[key] = value.strip()
        
        if any(product_data.values()):
            all_data.append(product_data)

    return all_data

if __name__ == "__main__":
    app.run()