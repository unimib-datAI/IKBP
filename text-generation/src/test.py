messages = [
    {"role": "system", "content": "something"},
    {"role": "user", "content": "hello"},
    {"role": "assitant", "content": "assistant"},
    {"role": "user", "content": "user"},
]

SYSTEM_BASE_PROMPT = f"""SYSTEM: You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."""
B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"


if messages[0]["role"] != "system":
    messages = [
        {
            "role": "system",
            "content": SYSTEM_BASE_PROMPT,
        }
    ] + messages

messages = [
    {
        "role": messages[1]["role"],
        "content": B_SYS + messages[0]["content"] + E_SYS + messages[1]["content"],
    }
] + messages[2:]

# print(messages)


for prompt, answer in zip(
    messages[::2],
    messages[1::2],
):
    print(prompt)
    print(answer)
