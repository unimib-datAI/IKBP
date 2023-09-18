import requests
import json

message = input("Message: ")

data = {
    "inputs": message,
}

r = requests.post("http://localhost:7862/count-tokens", json=data)

if r.status_code == 200:
    print(r.json())
else:
    print("Request failed with status code:", r.status_code)
