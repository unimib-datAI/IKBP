import requests


class DocumentRetriever:
    def __init__(self, url: str):
        self.url = url

    def retrieve(self, id: str):
        res = requests.get(self.url + "/" + str(id))
        return res.json()
