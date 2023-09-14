import requests
import json

# prompt = "###Human: {message}?###Assistant:"

message = input("Message: ")

# inputs = prompt.replace("{message}", message)

data = {
    "messages": [
        {"role": "user", "content": message},
        # {
        #     "role": "assistant",
        #     "content": """Of course! Natural Language Processing (NLP) is a subfield of artificial intelligence (AI) that focuses on interacting with humans using natural language. One common application of NLP is named entity recognition (NER), which involves identifying and categorizing entities mentioned in text into predefined categories such as person, organization, location, etc. For instance, if I were to say "John Smith works at Apple", John Smith would be an entity and Apple would be another entity. Does this help clarify things for you?""",
        # },
    ],
    # "max_new_tokens": 256
    # [DEFAULTS]:
    # temperature: 0.7,
    # top_k: 20,
    # top_p: 0.65,
    # min_p: 0.06,
    # token_repetition_penalty_max: 1.15,
    # token_repetition_penalty_sustain: 256,
    # token_repetition_penalty_decay: 128,
    # stream: true,
}

r = requests.post("http://localhost:7862/generate", json=data, stream=True)

if r.status_code == 200:
    for chunk in r.iter_content():
        if chunk:
            print(chunk.decode("utf-8"), end="", flush=True)
else:
    print("Request failed with status code:", r.status_code)
