import openai

class LLMService:
    def __init__(self, api_key):
        openai.api_key = api_key

    def generate_portfolio_insights(self, portfolio):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Provide insights on the following portfolio: {portfolio}"}
            ]
        )
        return response['choices'][0]['message']['content']

    def provide_risk_advice(self, portfolio):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"What are the risks associated with the following portfolio? {portfolio}"}
            ]
        )
        return response['choices'][0]['message']['content']

    def generate_rebalancing_recommendations(self, portfolio):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Suggest rebalancing recommendations for the following portfolio: {portfolio}"}
            ]
        )
        return response['choices'][0]['message']['content']
