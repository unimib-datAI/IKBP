import requests


class DocumentRetriever:
    def __init__(self, url: str):
        self.url = url

    def retrieve(self, id: str):
        res = requests.get(self.url + "/" + str(id))
        doc = res.json()
        try:
            del doc["annotation_sets"]
        except KeyError:
            pass
        return doc
