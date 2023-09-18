import argparse
import requests
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()  

class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["Authorization"] = "Bearer " + self.token
        return r

def stream_completion(options: dict):
  instruction_opt = options['instruction']

  def generate(instruction = None):
    if not instruction:
    # Get user input
      instruction = input('Prompt: ')
    
    resolved_options = {
      **options,
      "instruction": instruction
    }

    print('Debug', {**resolved_options, "stream": True})
    res = requests.post('https://vm.chronos.disco.unimib.it/llm/completion', json={**resolved_options, "stream": True}, stream=True, auth=BearerAuth(os.getenv('API_KEY')))

    for chunk in res.iter_lines():
        if chunk:
          decoded_chunk = chunk.decode("utf-8")
          parsed_chunk = json.loads(decoded_chunk)
          sys.stdout.write(parsed_chunk['text'])
          sys.stdout.flush()
          
    sys.stdout.write('\n')
    sys.stdout.flush()

  # try:
  if instruction_opt:
    generate(instruction=instruction_opt)
  else:
    while True:
      generate(instruction=instruction_opt)
      print('\n')
        

def completion(options: dict):
  instruction_opt = options['instruction']
  
  def generate(instruction=None):
    if not instruction:
      instruction = input("Prompt: ")

    resolved_options = {
      **options,
      "instruction": instruction
    }
    res = requests.post('http://127.0.0.1:8000/completion', json={**resolved_options, "stream": False})

    print(res.json()['text'])

  if instruction_opt:
    generate(instruction=instruction_opt)
  else:
    while True:
      generate(instruction=instruction_opt)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--stream', action='store_true')
  parser.add_argument('--no-stream', dest='stream', action='store_false')
  parser.set_defaults(feature=False)
  parser.add_argument('--p', dest='prompt', default=None, type=str)
  args = parser.parse_args()

  prompt = args.prompt

  options = {
    "instruction": prompt
  }

  if args.stream:
    stream_completion(options)
  else:
    completion(options)





