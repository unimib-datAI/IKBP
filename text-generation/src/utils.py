from __future__ import annotations
import torch
from transformers import GenerationConfig, TextIteratorStreamer
from threading import Thread


def llama_v2_prompt(
    messages: list[dict], max_new_tokens: int, min_token_reply: int = 256
):
  B_INST, E_INST = "[INST]", "[/INST]"
  B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"
  BOS, EOS = "<s>", "</s>"
  DEFAULT_SYSTEM_PROMPT = f"""SISTEMA: Sei un assistente disponibile, rispettoso e onesto. Rispondi sempre nel modo più utile possibile, garantendo la sicurezza. Assicurati che le tue risposte siano socialmente imparziali e positive. Se una domanda non ha senso o non è coerente dal punto di vista fattuale, spiega il motivo anziché fornire una risposta non corretta. Se non conosci la risposta a una domanda, per favore non diffondere informazioni false."""

  if messages[0]["role"] != "system":
    messages = [
        {
            "role": "system",
            "content": DEFAULT_SYSTEM_PROMPT,
        }
    ] + messages
  messages = [
    {
        "role": messages[1]["role"],
        "content": B_SYS + messages[0]["content"] + E_SYS + messages[1]["content"],
    }
  ] + messages[2:]

  messages_list = [
    f"{BOS}{B_INST} {(prompt['content']).strip()} {E_INST} {(answer['content']).strip()} {EOS}"
    for prompt, answer in zip(messages[::2], messages[1::2])
  ]
  messages_list.append(f"{BOS}{B_INST} {(messages[-1]['content']).strip()} {E_INST}")

  final_prompt = "".join(messages_list)
  print(final_prompt, flush=True)

  return final_prompt


def prepare_message(messages, max_new_tokens, min_token_reply = 256):
  return (
    llama_v2_prompt(messages, max_new_tokens, min_token_reply),
    max_new_tokens,
  )

# def tokenize(options):
#   tokenizer = options.pop("tokenizer")
#   tokenizer_options = options.pop("tokenizer_options")
#   prompt = generate_prompt(tokenizer_options.text, None)
#   inputs = tokenizer(prompt, return_tensors="pt")
#   return inputs


def generate_streaming_completion(options):
  model = options.pop("model")
  tokenizer = options.pop("tokenizer")
  model_options = options.pop("model_options")
  prompt = options.pop('message')

  generation_config = GenerationConfig(
    temperature=model_options.temperature,
    top_p=model_options.top_p,
    top_k=model_options.top_k,
    num_beams=model_options.num_beams,
    max_new_tokens=model_options.max_new_tokens,
    do_sample=model_options.temperature > 0
  )

  inputs = tokenizer(prompt, return_tensors="pt")
  input_ids = inputs["input_ids"].cuda()
  streamer = TextIteratorStreamer(tokenizer,skip_prompt=True)

  def generate():
    with torch.no_grad():
      model.eval()
      model.generate(
          input_ids=input_ids,
          generation_config=generation_config,
          streamer=streamer,
          return_dict_in_generate=True,
      )
      print('STREAMING DONE', flush=True)
    torch.cuda.empty_cache()

  Thread(target=generate,args=()).start()

  for index, new_text in enumerate(streamer):
      if index > 0:
        if new_text:
          yield new_text

def generate_completion(options):
  model = options.pop("model")
  tokenizer = options.pop("tokenizer")
  model_options = options.pop("model_options")
  prompt = options.pop('message')

  generation_config = GenerationConfig(
    temperature=model_options.temperature,
    top_p=model_options.top_p,
    top_k=model_options.top_k,
    num_beams=model_options.num_beams,
    max_new_tokens=model_options.max_new_tokens,
  )

  inputs = tokenizer(prompt, return_tensors="pt")
  input_ids = inputs["input_ids"].cuda()

  with torch.no_grad():
    model.eval()
    generation_output = model.generate(
        input_ids=input_ids,
        generation_config=generation_config,
        return_dict_in_generate=True
    )
    torch.cuda.empty_cache()

  output = tokenizer.decode(generation_output.sequences[0])
  del generation_output
  
  return {
    "text": output.split("### Response:")[1].strip()
  }