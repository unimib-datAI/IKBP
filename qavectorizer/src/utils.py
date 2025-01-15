import multiprocessing


def get_hits(search_res):
    def convert_hit(hit):
        text = hit["_source"].pop("text")
        rest = {**hit["_source"]}
        # if "annotations" in rest:
        #     del  rest["annotations"]
        # del rest["annotations"]
        # if "chunks" in rest:
        #     del  rest["chunks"]
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


def group_facets(facets):
    return_facets = []
    for facets_group in facets:
        grouped_facets = {}
        for facet in facets_group["children"]:
            facet_display_name = facet["display_name"].lower()
            if facet_display_name not in grouped_facets:
                grouped_facets[facet_display_name] = facet
                grouped_facets[facet_display_name]["ids_ER"] = [facet["key"]]
            else:
                grouped_facets[facet_display_name]["doc_count"] += facet["doc_count"]
                grouped_facets[facet_display_name]["ids_ER"].append(facet["key"])
        facets_group["children"] = [grouped_facets[key] for key in grouped_facets]
    return facets


def collect_chunk_ranks(response):
    ranks = {}
    temp_rank = 1
    for rank, hit in enumerate(response["hits"]["hits"]):
        doc_id = hit["_source"]["id"]
        if "inner_hits" in hit and "chunks.vectors" in hit["inner_hits"]:
            for chunk_hit in hit["inner_hits"]["chunks.vectors"]["hits"]["hits"]:
                chunk_id = chunk_hit["fields"]["chunks"][0]["vectors"][0]["text"][0]
                combined_id = (doc_id, chunk_id)
                ranks[combined_id] = temp_rank  # Avoid division by zero
                temp_rank += 1
    return ranks


def collect_chunk_ranks_full_text(response):
    ranks = {}
    temp_rank = 1
    for rank, hit in enumerate(response["hits"]["hits"]):
        doc_id = hit["_source"]["id"]
        if "inner_hits" in hit and "chunks" in hit["inner_hits"]:
            for chunk_hit in hit["inner_hits"]["chunks"]["hits"]["hits"]:
                chunk_id = chunk_hit["fields"]["chunks"][0]["vectors"][0]["text"][0]
                combined_id = (doc_id, chunk_id)
                ranks[combined_id] = temp_rank  # Avoid division by zero
                temp_rank += 1
    return ranks


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


def get_facets_metadata(search_res):

    metadata_type_buckets = {}
    for document in search_res["hits"]["hits"]:
        if "metadata" not in document["_source"]:
            continue
        for mention in document["_source"]["metadata"]:
            if mention["type"] not in metadata_type_buckets:
                metadata_type_buckets[mention["type"]] = []
            metadata_type_buckets[mention["type"]].append(mention)

    metadata_facets = []

    for bucket_key in metadata_type_buckets.keys():
        final_bucket = {}
        final_bucket["key"] = bucket_key

        final_bucket["doc_count"] = len(metadata_type_buckets[bucket_key])
        aggregated_data = {}

        # Loop through the list of objects
        for obj in metadata_type_buckets[bucket_key]:
            # If the 'name' of the object is not in the dictionary, add the object to the dictionary
            if obj["value"] not in aggregated_data:
                appended_obj = obj
                appended_obj["doc_count"] = 1
                aggregated_data[obj["value"]] = obj
            else:
                # If the 'name' of the object is already in the dictionary, increment the count
                aggregated_data[obj["value"]]["doc_count"] += 1
        children = []
        for mention in aggregated_data.keys():
            ment = aggregated_data[mention]
            child = {
                "key": mention,
                "display_name": mention,
                "doc_count": ment["doc_count"],
            }
            children.append(child)
        final_bucket["children"] = children
        final_bucket["n_children"] = len(children)
        metadata_facets.append(final_bucket)
    return metadata_facets


def anonymize(s):
    words = s.split()
    new_words = ["".join([word[0]] + ["*" * (len(word) - 1)]) for word in words]
    return " ".join(new_words)
