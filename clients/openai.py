import openai
import os


class OpenAIClient:
    def __init__(self, api_key: str = None):
        if api_key:
            openai.api_key = api_key
        else:
            openai.api_key = os.environ.get("OPENAI_API_KEY", None)
        if not openai.api_key:
            raise ValueError("A valid OpenAI API key is required.")
        
        self.default_model = "gpt-3.5-turbo"
        self.supported_models = ["gpt-3.5-turbo"]
        

    def get_llm_response(self, system_prompt, user_prompt, model=None, **kwargs):
        try:
            completion = openai.chat.completions.create(
                model=model if model in self.supported_models else self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kwargs
            )
            response = completion.choices[0].message.content
            return response
        except KeyError:
            print("Failed to retrieve response from OpenAI.")
        except Exception as e:
            print(f"OpenAI Error: {e}")
