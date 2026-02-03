# asin_api.py
import requests


def fetch_asins(skus: list) -> list[str]:
    url = "https://bcp-ai.vercel.app/api/bigquery/demand/fetchasins"
    headers = {"Content-Type": "application/json"}

    # Ensure the SKUs are formatted correctly in the request body
    skus_str = ", ".join(f"'{sku}'" for sku in skus)
    body = {"sku": skus_str}

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        print("ASINs fetched successfully!")
        response_json = response.json()
        asin_list = [item["asin"] for item in response_json]
        return asin_list
    else:
        print(f"Failed to fetch ASINs, Status Code: {response.status_code}")
        return None


asins = fetch_asins(["SKY6105"])
print(asins)
