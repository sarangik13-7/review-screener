Below is an in-depth README that explains the workflow, architecture, and execution of the project:

---

# Amazon Review Compliance Checker

This project provides an end-to-end solution for scraping Amazon product reviews, evaluating them against community guidelines using OpenAI's GPT-4 model, and publishing non-compliant reviews to Google Cloud Pub/Sub for downstream processing. It integrates web scraping, AI-powered content moderation, and cloud-based messaging to automate the review monitoring process.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [Components](#components)
  - [Data Flow](#data-flow)
- [Setup & Prerequisites](#setup--prerequisites)
- [Execution](#execution)
  - [Running the Flask API](#running-the-flask-api)
  - [Triggering Review Processing & Publishing](#triggering-review-processing--publishing)
  - [Listening for Published Messages](#listening-for-published-messages)
- [Customization & Configuration](#customization--configuration)
- [Conclusion](#conclusion)

---

## Overview

The project automates the process of monitoring and ensuring compliance of Amazon product reviews. Given a list of SKU codes, the system performs the following tasks:

1. **Fetches ASINs:** Maps SKU codes to ASINs using an external API.
2. **Scrapes Reviews:** Uses Selenium and BeautifulSoup to scrape reviews and product details from Amazon.
3. **Screens Reviews:** Uses OpenAI's GPT-4 model (via LangChain) to check each review against a set of predefined community guidelines.
4. **Publishes Results:** Non-compliant reviews are published to a Google Cloud Pub/Sub topic.
5. **Subscribes & Processes:** A subscriber listens to the Pub/Sub topic and processes the non-compliant reviews (e.g., saving to a file for further analysis).

---

## Architecture

### Components

- **Flask API (`app.py`):**  
  Exposes a `/process_reviews` endpoint that accepts a JSON payload containing a list of SKU codes. It coordinates the fetching of ASINs, scraping reviews, and screening reviews for compliance.

- **ASIN Fetcher (`asin_api.py`):**  
  Contains a function to call an external API to retrieve Amazon Standard Identification Numbers (ASINs) corresponding to given SKU codes.

- **Review Scraper (`star_scraper.py`):**  
  Utilizes Selenium (with headless browsing and captcha bypass capabilities) and BeautifulSoup to scrape review data and product information from Amazon pages.

- **Review Screener (`screener.py`):**  
  Implements a two-step review compliance check using GPT-4:
  - **Initial Screening:** Checks if reviews comply with Amazon's community guidelines.
  - **Recheck:** For reviews flagged as non-compliant, a secondary evaluation determines the degree of non-compliance and highlights the specific guideline violations.

- **Publisher (`publisher.py`):**  
  Calls the Flask API to process reviews and then publishes the non-compliant reviews to a designated Google Cloud Pub/Sub topic.

- **Subscriber (`subscriber.py`):**  
  Listens to the Pub/Sub topic, retrieves the non-compliant reviews messages, and processes them (e.g., by appending the data to an output JSON file).

### Data Flow

1. **Input Request:**  
   A POST request is sent to `/process_reviews` with a JSON payload containing a list of SKU codes.

2. **ASIN Mapping:**  
   `asin_api.py` takes the SKUs, formats them, and calls an external API to fetch the corresponding ASINs.

3. **Review Scraping:**  
   For each ASIN, `star_scraper.py` navigates to the product and review pages on Amazon. It scrapes reviews, bypasses captchas when necessary, and collects product details.

4. **Review Screening:**  
   The scraped review data is passed to the `Screener` class in `screener.py`:
   - **Step 1:** Each review is evaluated against a set of community guidelines.
   - **Step 2:** Reviews identified as non-compliant are rechecked to provide detailed reasons and quantify the extent of the violation.
   - Results (non-compliant reviews) are written to a JSON file for record-keeping.

5. **Publishing Results:**  
   Once the Flask API returns the non-compliant reviews, `publisher.py` publishes this data to a Google Cloud Pub/Sub topic.

6. **Message Consumption:**  
   `subscriber.py` listens to the Pub/Sub topic. When messages are received, they are processed and stored locally (e.g., appended to a file).

---

## Setup & Prerequisites

- **Python 3.x**  
- **Required Libraries:**  
  - Flask
  - Requests
  - Selenium
  - BeautifulSoup4
  - LangChain & langchain_openai
  - google-cloud-pubsub
  - webdriver-manager
  - Other utility libraries (e.g., `json`, `os`, etc.)

- **Google Cloud Credentials:**  
  Ensure that you have a service account JSON file (update the path in both `publisher.py` and `subscriber.py`).

- **Environment Variables:**  
  - `OPENAI_API_KEY`: Your OpenAI API key.
  - `EMAIL` & `PWD`: Credentials for Amazon sign-in (used in the scraping process).

- **ChromeDriver:**  
  Managed automatically via `webdriver-manager` (ensure Chrome is installed).

---

## Execution

### Running the Flask API

Start the Flask server by running:

```bash
python app.py
```

The server listens on `0.0.0.0` and port `8080` (or the port specified by the `PORT` environment variable).

### Triggering Review Processing & Publishing

1. **Sending a Request:**  
   Use a tool like Postman or `curl` to send a POST request to the API endpoint:

   ```bash
   curl -X POST http://localhost:8080/process_reviews \
   -H "Content-Type: application/json" \
   -d '{"sku_list": ["SKU123", "SKU456"]}'
   ```

2. **Processing:**  
   The Flask API:
   - Fetches the corresponding ASINs via `asin_api.py`
   - Uses `star_scraper.py` to scrape reviews and product info from Amazon
   - Processes reviews in batches using `screener.py` to detect non-compliant content

3. **Publishing to Pub/Sub:**  
   After processing, `publisher.py` calls the Flask API to retrieve non-compliant reviews and then publishes them to a designated Google Cloud Pub/Sub topic. Run the publisher script using:

   ```bash
   python publisher.py
   ```

### Listening for Published Messages

Run the subscriber script to start listening for non-compliant review messages:

```bash
python subscriber.py
```

Messages received from Pub/Sub will be processed by the `callback` function and appended to a file (e.g., `non_compliant_reviews_output.json`).

---

## Customization & Configuration

- **Review Guidelines:**  
  The compliance guidelines in `screener.py` can be updated to reflect any changes in policy or additional requirements.

- **Batch Size & Processing:**  
  Modify the `batch_size` variable in `screener.py` if you need to process a different number of reviews concurrently.

- **Scraper Settings:**  
  Adjust Selenium options (e.g., headless mode, incognito settings) in `star_scraper.py` based on your scraping environment or debugging needs.

- **Pub/Sub Topics & Subscriptions:**  
  Update the topic paths and subscription names in `publisher.py` and `subscriber.py` to align with your Google Cloud configuration.

---

## Conclusion

This project offers a robust pipeline for monitoring Amazon reviews, ensuring they comply with community guidelines, and automating further processing via cloud-based messaging. It can be extended or integrated with additional systems (e.g., dashboards, databases, alert systems) to provide comprehensive oversight and moderation of customer reviews.

---

Feel free to contribute, modify, and extend this project as needed for your specific use cases.

Happy Coding!