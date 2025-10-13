import argparse
from fastapi import FastAPI, Body
from pydantic import BaseModel
import uvicorn
import spacy
from spacy.cli import download as spacy_download
import os
from gatenlp import Document

DEFAULT_TAG = "aplha_v0.1.0_spacy"
model = ""
tag = "merged"
senter = False
spacy_pipeline = None
gpu_id = -1


class Item(BaseModel):
    text: str


app = FastAPI()


def restructure_newline(text):
    return text.replace("\n", " ")


@app.post("/api/spacyner")
async def encode_mention(doc: dict = Body(...)):
    print("handling ner for document")
    try:
        global model
        global senter
        global tag
        global spacy_pipeline

        # replace wrong newlines
        text = restructure_newline(doc["text"])

        # Tokenize and split into chunks of max 512 tokens
        nlp = spacy_pipeline
        # Only run spaCy once for tokenization
        tokens = []
        try:
            doc_spacy = nlp(text)
            tokens = [token for token in doc_spacy]
        except Exception as e:
            print("SpaCy tokenization error:", e)
            return {"error": "SpaCy tokenization failed"}

        chunks = []
        chunk_size = 512
        if len(tokens) == 0:
            chunks = [(text, 0, len(text))]
        else:
            for i in range(0, len(tokens), chunk_size):
                chunk_tokens = tokens[i : i + chunk_size]
                start_char = chunk_tokens[0].idx
                end_char = chunk_tokens[-1].idx + len(chunk_tokens[-1].text)
                chunk_text = text[start_char:end_char]
                chunks.append((chunk_text, start_char, end_char))

        # Prepare main doc
        doc_gatenlp = Document.from_dict(doc)
        entity_set = doc_gatenlp.annset("entities_{}".format(tag))
        if senter:
            sentence_set = doc_gatenlp.annset("sentences_{}".format(tag))

        for chunk_text, chunk_start, _ in chunks:
            chunk_doc = nlp(chunk_text)
            # Sentences
            if senter:
                for sent in chunk_doc.sents:
                    sentence_set.add(
                        chunk_start + sent.start_char,
                        chunk_start + sent.end_char,
                        "sentence",
                        {"source": "spacy", "spacy_model": model},
                    )
            # Entities
            for ent in chunk_doc.ents:
                feat_to_add = {
                    "ner": {
                        "type": ent.label_,
                        "score": 1.0,
                        "source": "spacy",
                        "spacy_model": model,
                    }
                }
                if ent.label_ == "DATE":
                    feat_to_add["linking"] = {"skip": True}
                entity_set.add(
                    chunk_start + ent.start_char,
                    chunk_start + ent.end_char,
                    ent.label_,
                    feat_to_add,
                )

        if not "pipeline" in doc_gatenlp.features:
            doc_gatenlp.features["pipeline"] = []
        doc_gatenlp.features["pipeline"].append("spacyner")

        return doc_gatenlp.to_dict()
    except Exception as e:
        print("Caught exception:", e)
        return {"error": str(e)}


def initialize():
    global model
    global senter
    global spacy_pipeline
    global gpu_id
    print("Loading spacy model...")
    # Load spacy model
    try:
        spacy_pipeline = spacy.load(
            model,
            exclude=[
                "tok2vec",
                "morphologizer",
                "tagger",
                "parser",
                "attribute_ruler",
                "lemmatizer",
            ],
        )
    except Exception as e:
        print("Caught exception:", e, "... Trying to download spacy model ...")
        spacy_download(model)
        spacy_pipeline = spacy.load(
            model,
            exclude=[
                "tok2vec",
                "morphologizer",
                "tagger",
                "parser",
                "attribute_ruler",
                "lemmatizer",
            ],
        )

    # gpu
    if gpu_id >= 0:
        gpu = spacy.prefer_gpu(gpu_id)
        print("Using", f"gpu {gpu}" if gpu else "cpu", flush=True)

    # sentences
    if senter:
        spacy_pipeline.enable_pipe("senter")

    print("Loading complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="host to listen at",
    )
    parser.add_argument(
        "--port",
        type=int,
        default="30304",
        help="port to listen at",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="en_core_web_sm",
        help="spacy model to load",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=DEFAULT_TAG,
        help="AnnotationSet tag",
    )
    parser.add_argument(
        "--sents",
        action="store_true",
        default=False,
        help="Do sentence tokenization",
    )
    parser.add_argument(
        "--gpu-id",
        type=int,
        default=-1,
        help="Spacy GPU id",
    )

    args = parser.parse_args()

    model = args.model
    senter = args.sents
    tag = args.tag
    gpu_id = args.gpu_id

    initialize()

    uvicorn.run(app, host=args.host, port=args.port)
else:
    model = os.environ.get("SPACY_MODEL")
    senter = os.environ.get("SPACY_SENTER", False)
    tag = os.environ.get("SPACY_TAG", "merged")
    gpu_id = int(os.environ.get("SPACY_GPU", -1))
    current_dir = os.getcwd()

    # Print the current directory path
    print("Current Directory:", current_dir)

    # List and print the contents of the directory
    contents = os.listdir(current_dir + "/models")
    print("Contents of the Current Directory:")
    for item in contents:
        print(item)
    initialize()
