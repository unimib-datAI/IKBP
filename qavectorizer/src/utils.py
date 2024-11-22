import multiprocessing


def get_hits(search_res):
    def convert_hit(hit):
        text = hit["_source"].pop("text")
        rest = {**hit["_source"]}
        rest["mongo_id"] = rest["mongoId"]
        rest["name"] = f'{rest["sender"]} -> {rest["receiver"]} \n {rest["timestamp"]}'
        del rest["mongoId"]
        del rest["annotations"]
        del rest["chunks"]
        return {"_id": hit["_id"], "text": text[:150], **rest}

    return [convert_hit(hit) for hit in search_res["hits"]["hits"]]


def get_facets_annotations(search_res):
    print()

    def convert_annotation_bucket(bucket):
        print()
        return {
            "key": bucket["key"],
            "n_children": len(bucket["mentions"]["buckets"]),
            "doc_count": bucket["doc_count"],
            "children": sorted(
                [
                    {
                        "key": children_bucket["key"],
                        "display_name": children_bucket["top_hits_per_mention"]["hits"][
                            "hits"
                        ][0]["_source"]["display_name"],
                        "is_linked": children_bucket["top_hits_per_mention"]["hits"][
                            "hits"
                        ][0]["_source"]["is_linked"],
                        "doc_count": children_bucket["doc_count"],
                    }
                    for children_bucket in bucket["mentions"]["buckets"]
                ],
                key=lambda x: x["display_name"],
            ),
        }

    return [
        convert_annotation_bucket(bucket)
        for bucket in search_res["aggregations"]["annotations"]["types"]["buckets"]
    ]


def get_facets_annotations_no_agg(hits):
    mentions_type_buckets = {}
    for document in hits["hits"]["hits"]:
        for mention in document["_source"]["annotations"]:
            if mention["type"] not in mentions_type_buckets:
                mentions_type_buckets[mention["type"]] = []
            mentions_type_buckets[mention["type"]].append(mention)

    ann_facets = []

    for bucket_key in mentions_type_buckets.keys():
        final_bucket = {}
        final_bucket["key"] = bucket_key

        final_bucket["doc_count"] = len(mentions_type_buckets[bucket_key])
        aggregated_data = {}

        # Loop through the list of objects
        for obj in mentions_type_buckets[bucket_key]:
            # If the 'name' of the object is not in the dictionary, add the object to the dictionary
            if obj["id_ER"] not in aggregated_data:
                appended_obj = obj
                appended_obj["doc_count"] = 1
                aggregated_data[obj["id_ER"]] = obj
            else:
                # If the 'name' of the object is already in the dictionary, increment the count
                aggregated_data[obj["id_ER"]]["doc_count"] += 1
        children = []
        for mention in aggregated_data.keys():
            ment = aggregated_data[mention]
            child = {
                "key": mention,
                "display_name": ment["display_name"],
                "doc_count": ment["doc_count"],
                "is_linked": ment["is_linked"],
            }
            children.append(child)
        final_bucket["children"] = children
        final_bucket["n_children"] = len(children)
        ann_facets.append(final_bucket)
    return ann_facets


def get_senders_and_receivers(hits):
    senders = []
    receivers = []
    for document in hits:
        if "sender" in document:
            senders.append(document["sender"])
        if "receiver" in document:
            receivers.append(document["receiver"])
    senders = list(set(senders))
    receivers = list(set(receivers))

    return [senders, receivers]


def get_facets_metadata(search_res):
    def convert_annotation_bucket(bucket):
        # filter empty velues. Some documents may not have some metadata
        children = [x for x in bucket["values"]["buckets"] if x["key"] != ""]

        return {
            "key": bucket["key"],
            "n_children": len(children),
            "doc_count": bucket["doc_count"],
            "children": children,
        }

    return [
        convert_annotation_bucket(bucket)
        for bucket in search_res["aggregations"]["metadata"]["types"]["buckets"]
    ]


def anonymize(s):
    words = s.split()
    new_words = ["".join([word[0]] + ["*" * (len(word) - 1)]) for word in words]
    return " ".join(new_words)
