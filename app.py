# app.py
import json
import os
from flask import Flask, request, jsonify
from asin_api import fetch_asins
from star_scraper import scrap_from_amazon
from screener import Screener

app = Flask(__name__)

# Initialize the Screener instance for screening non-compliant reviews
screener = Screener()

@app.route('/process_reviews', methods=['POST'])
def process_reviews():
    """
    Endpoint to process reviews based on SKU.
    Expects a JSON payload with SKU codes.
    """
    data = request.json
    sku_list = data.get("sku_list", [])

    # Fetch ASINs for the given list of SKU codes
    asins = fetch_asins(skus=sku_list)
    all_non_compliant_reviews = {}

    for asin, sku in zip(asins, sku_list):
        # Scrape reviews from Amazon for the given ASIN and SKU number
        scrap_data = scrap_from_amazon(asin_number=asin, sky_number=sku)
        # Process the scraped reviews to find non-compliant ones
        non_compliant_reviews = screener.process_reviews(scrap_data)
        if non_compliant_reviews:
            all_non_compliant_reviews[sku] = non_compliant_reviews

    return jsonify(all_non_compliant_reviews)

if __name__ == '__main__':
    # Ensure the app runs on the specified host and port for Google Cloud
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
