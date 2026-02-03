# screener.py
import os
from langchain_openai import OpenAI, ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json
import time
from langchain_community.callbacks import get_openai_callback
from dotenv import load_dotenv

load_dotenv(override=True)

class Screener:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key = self.api_key)
        self.guidelines = """
1. Reviews must not mention sellers, customer service, ordering issues, returns, shipping, or damage during.
2. Acceptable if related to product value. No individual pricing experiences or specific store availability.
3. **Supported languages only**: Reviews must be in the site's supported languages (English and Spanish on Amazon.com).
4. **No spam or repetitive content**: Avoid repetitive text, excessive punctuation, symbols, or spam.
5. **No private information**: Exclude personal information like phone numbers, emails, addresses, or order numbers.
6. No profanity, harassment, threats, personal attacks, libel, or defamation.
7. Excludes hate based on race, ethnicity, nationality, gender, sexual orientation, religion, age, or disability.
8. **No explicit sexual content**: Avoid nudity, sexually explicit images, or descriptions.
9. **No external links**: Only links to other Amazon products are allowed; no external sites or affiliate links.
10. **No promotional content**: Reviews must not promote other companies, websites, or have conflicts of interest without clear disclosure.
11. **No compensated reviews**: Reviews should not be in exchange for compensation, except through the Amazon Vine program.
12. **Original content only**: No plagiarism, impersonation, or infringement of intellectual property.
13. **No illegal activity promotion**: Avoid encouraging illegal activities, violence, drug use, underage drinking, fraud, or dangerous product misuse.
14. **No medical claims**: Do not make claims about preventing or curing serious medical conditions.

Evaluate and answer in detail why the review is not compliant.
"""
        self.prompt_template_1 = """
You are tasked with rigorously evaluating product reviews based on Amazon's community guidelines. For each review, determine if it complies with the guidelines and provide a short explanation. 

Amazon Community Guidelines:
{{guidelines}}

Here are reviews. For each review, give the following output, indicating if that particular review is compliant or not. And if non-compliant, explain the reason behind the non-compliance.
Give the output in the following format: 
{
"1":{
    "result" : "No Or yes",
    "reason" : "If no then why"
},
"2":{
    "result" : "No Or yes",
    "reason" : "If no then why"
}
}
{{reviews_text}}
        """
        self.prompt_template_2 = """
You are tasked with rigorously evaluating product reviews based on Amazon's community guidelines. Each review has been initially assessed for compliance. Your task is to cross-verify the provided result and reason, making corrections if necessary. Additionally, determine the percentage of the review content that contributes to non-compliance if applicable. In the reason, mention the guideline(s) that is/are being violated.

Amazon Community Guidelines:
{{guidelines}}

Here are the reviews along with their initial evaluations. For each review, confirm or correct the "result" and "reason" and calculate the "percentage_of_relevance" if the review is non-compliant. The percentage_of_relevance represents the proportion of the review content that violates the guidelines. For example, if a review has 10 sentences and 1 sentence violates a guideline, the percentage_of_relevance would be 10%. This helps quantify the extent of non-compliance within the review.

Provide the output in the following format:
{
"1":{
    "result" : "No Or YES",
    "reason" : "If yes then why",
    "percentage_of_relevance": "x%"
},
"2":{
    "result" : "No Or YES",
    "reason" : "If yes then why",        
    "percentage_of_relevance": "x%"
}
}

Reviews:-
{{reviews_text}}
"""

    def check_reviews_compliance(self, reviews):
        reviews_text = ""
        for i, review in enumerate(reviews, 1):
            reviews_text += f"""
            Review: {i}
            Body: {review['body']}
            """

        self.prompt_1 = self.prompt_template_1.replace(
            "{{guidelines}}", self.guidelines
        ).replace("{{reviews_text}}", reviews_text)

        messages_1 = [
            SystemMessage(
                content="You are an expert moderator following Amazon's community guidelines."
            ),
            HumanMessage(content=self.prompt_1),
        ]

        start_time = time.time()
        with get_openai_callback() as cb:
            response = self.llm.invoke(messages_1)
            token_usage = cb.total_tokens
        end_time = time.time()
        response_content = response.content

        if "```json" in response_content:
            response_content = response_content[7:]
            response_content = response_content[:-3]
        # print(response_content)

        result = {
            "response": json.loads(response_content),
            "tokens": token_usage,
            "time_taken": end_time - start_time,
        }

        return result

    def recheck_reviews_compliance(self, reviews):
        reviews_text = str()
        for i, review in enumerate(reviews, 1):
            reviews_text += f"""
            Review: {i}
            Body: {review['body']}
            Result: {review['result']}
            Reason: {review['reason']}
            """
        self.prompt_2 = self.prompt_template_2.replace(
            "{{guidelines}}", self.guidelines
        ).replace("{{reviews_text}}", reviews_text)
        messages_2 = [
            SystemMessage(
                content="You are an expert moderator following Amazon's community guidelines."
            ),
            HumanMessage(content=self.prompt_2),
        ]
        start_time = time.time()
        with get_openai_callback() as cb:
            response = self.llm.invoke(messages_2)
            token_usage = cb.total_tokens
        end_time = time.time()
        response_content = response.content

        if "```json" in response_content:
            response_content = response_content[7:]
            response_content = response_content[:-3]
        print(response_content)

        result = {
            "response": json.loads(response_content),
            "tokens": token_usage,
            "time_taken": end_time - start_time,
        }

        return result

    def process_reviews(self, data: dict):
    # def process_reviews(self, file_path:str):
    #     with open(file_path, "r") as file:
    #         data = json.load(file)
        reviews = data["reviews"]
        asin = data["asin"]
        # sky = data["sky"]
        batch_size = 25
        results = []
        total_tokens = 0
        total_time = 0

        non_compliant_reviews = []

        # Initial processing of reviews
        for i in range(0, len(reviews), batch_size):
            try:
                batch_reviews = reviews[i : i + batch_size]
                compliance_results = self.check_reviews_compliance(batch_reviews)

                total_tokens += compliance_results["tokens"]
                total_time += compliance_results["time_taken"]

                for idx, review in enumerate(batch_reviews, start=1):
                    try:
                        result = {
                            "title": review["title"],
                            "rating": review["rating"],
                            "body": review["body"],
                            "result": compliance_results["response"][str(idx)][
                                "result"
                            ],
                            "reason": compliance_results["response"][str(idx)][
                                "reason"
                            ],
                        }
                        results.append(result)
                        if result["result"].lower() == "no":
                            non_compliant_reviews.append(result)
                    except Exception as e:
                        print(e)
                        pass
            except Exception as e:
                print(e)
                pass

        # Reprocess non-compliant reviews
        recheck_results = []
        for i in range(0, len(non_compliant_reviews), batch_size):
            try:
                batch_reviews = non_compliant_reviews[i : i + batch_size]
                recheck_compliance_results = self.recheck_reviews_compliance(
                    batch_reviews
                )

                total_tokens += recheck_compliance_results["tokens"]
                total_time += recheck_compliance_results["time_taken"]

                for idx, review in enumerate(batch_reviews, start=1):
                    try:
                        result = {
                            "asin": asin,
                            # "sky": sky,
                            "title": review["title"],
                            "rating": review["rating"],
                            "body": review["body"],
                            "result": recheck_compliance_results["response"][str(idx)][
                                "result"
                            ],
                            "reason": recheck_compliance_results["response"][str(idx)][
                                "reason"
                            ],
                            "percentage_of_relevance": recheck_compliance_results[
                                "response"
                            ][str(idx)]["percentage_of_relevance"],
                        }
                        if result["result"].lower() == "no":
                            recheck_results.append(result)
                    except Exception as e:
                        print(e)
                        pass
            except Exception as e:
                print(e)
                pass

        # # Save initial results
        # with open("compliance_results.json", "w") as outfile:
        #     json.dump(results, outfile, indent=2) 

        # Save recheck results
        with open(f"./nc_reviews/{asin}_noncompliant_reviews.json", "w") as outfile:
            json.dump(recheck_results, outfile, indent=2)

        print(f"Total tokens used: {total_tokens}")
        print(f"Total time taken: {total_time} seconds")
        return recheck_results


if __name__ == "__main__":
    screener = Screener()
    for file in os.listdir("./reviews_file_generator/output"):
        screener.process_reviews(
            f"D:/BCP/Reviews Screener - Copy/reviews_pipeline/reviews_file_generator/output/{file}"
        )
