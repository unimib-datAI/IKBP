from gatenlp import Document
import json
import numpy as np
from numpy.linalg import norm
import base64
import itertools
import networkx as nx
from networkx.algorithms.community import louvain_communities
import textdistance
import pickle

def import_document(file_path):
    # import
    with open(file_path, 'r') as f:
        doc = json.load(f)
        doc = Document.from_dict(doc)
    return doc

def vector_decode(s, dtype=np.float32):
    buffer = base64.b64decode(s)
    v = np.frombuffer(buffer, dtype=dtype)
    return v

def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b)/(norm(vec_a)*norm(vec_b))

def sourface_similarity(text_a, text_b):
    jaro = textdistance.JaroWinkler()
    jaro_bi = textdistance.JaroWinkler(qval=2)
    jaro_tri = textdistance.JaroWinkler(qval=3)
    jaro_four = textdistance.JaroWinkler(qval=4)
    damer_bi = textdistance.DamerauLevenshtein(qval=2)
    jaccard = textdistance.Jaccard()
    cosine = textdistance.Cosine()
    bag = textdistance.Bag()
    subsequence = textdistance.LCSSeq()

    score = [jaro.normalized_similarity(text_a, text_b),
             jaro_bi.normalized_similarity(text_a, text_b),
             jaro_tri.normalized_similarity(text_a, text_b),
             jaro_four.normalized_similarity(text_a, text_b),
             damer_bi.normalized_similarity(text_a, text_b),
             jaccard.normalized_similarity(text_a, text_b),
             cosine.normalized_similarity(text_a, text_b),
             bag.normalized_similarity(text_a, text_b),
             subsequence.normalized_similarity(text_a, text_b)]
    return score

def compute_similarity(array_idx_a, array_idx_b, text_a, text_b, matr_embd, decimal='', uncased=True):
    if uncased:
        text_a = text_a.lower()
        text_b = text_b.lower()
    embd_a = matr_embd[array_idx_a]
    embd_b = matr_embd[array_idx_b]
    score = sourface_similarity(text_a, text_b) + [cosine_similarity(embd_a, embd_b)]
    if decimal:
        score = [round(s, decimal) for s in score]
    return score

def make_clusters(doc_dict, model, annset_name='entities_', threshold=0.64, seed=11, separate_annset=False):
    doc = Document.from_dict(doc_dict)
    annset = doc.annset(annset_name)
    
    # Filter annotations that have linking encodings
    valid_annotations = []
    for ann in annset:
        if ('linking' in ann.features and 
            'encoding' in ann.features['linking']):
            valid_annotations.append(ann)
    
    if not valid_annotations:
        # If no annotations have encodings, return the document unchanged
        print(f"Warning: No annotations with linking encodings found in annotation set '{annset_name}'")
        return doc
    
    if len(valid_annotations) < 2:
        # If we have less than 2 annotations, no clustering can be performed
        print(f"Warning: Only {len(valid_annotations)} annotation(s) with encodings found. Need at least 2 for clustering.")
        # Still add cluster info for the single annotation if it exists
        if len(valid_annotations) == 1:
            ann = valid_annotations[0]
            ann.features['cluster'] = 0
            doc.features['clusters'] = {}
            clusters_info = [{
                'title': doc.text[ann.start:ann.end].replace('\n',' '),
                'id': 0,
                'type': ann.type,
                'mentions': [{'id': ann.id, 'mention': doc.text[ann.start:ann.end].replace('\n',' ')}]
            }]
            doc.features['clusters'][annset_name] = clusters_info
        return doc
    
    # Process only annotations with valid encodings
    matr_embd = np.array([vector_decode(ann.features['linking']['encoding']) for ann in valid_annotations])
    annset_ids = [a.id for a in valid_annotations]
    # Create mapping from annotation ID to array index
    id_to_idx = {ann_id: idx for idx, ann_id in enumerate(annset_ids)}
    pairs = np.array(list(itertools.combinations(annset_ids, 2)))
    # compute similarity
    X_test=[]
    for idx_a, idx_b in pairs:
        text_a = doc.text[annset[idx_a].start:annset[idx_a].end]
        text_b = doc.text[annset[idx_b].start:annset[idx_b].end]
        # Use the mapping to get the correct array indices
        array_idx_a = id_to_idx[idx_a]
        array_idx_b = id_to_idx[idx_b]
        X_test.append(compute_similarity(array_idx_a, array_idx_b, text_a, text_b, matr_embd, 5, uncased=True))
    X_test = np.array(X_test)
    # compute probabilities
    proba = model.predict_proba(X_test)
    # make graph
    graph = nx.Graph()
    similarity_matrix = np.identity(max(annset_ids) + 1)
    for p, (idx_a, idx_b) in zip(proba[:,1], pairs):
        similarity_matrix[idx_a, idx_b] = p
        similarity_matrix[idx_b, idx_a] = p
        if p>=threshold:
            graph.add_edge(idx_a, idx_b, weight=p)
    # create clusters
    clusters = louvain_communities(graph, resolution=2, seed=seed)
    clusters = [list(c) for c in clusters]
    # refine cluster
    clusters_refine = []
    for cluster in clusters:
        new_cluster = []
        for idx_target in cluster:
            score = []
            for idx_other in list(set(cluster) - set([idx_target])):
                score.append(similarity_matrix[idx_target, idx_other])
            mean_score = np.array(score).mean()
            if mean_score>=threshold:
                new_cluster.append(int(idx_target))
        clusters_refine.append(new_cluster)
    # create cluster2id
    cluster2id = {}
    ann_in_cluster = []
    for c_idx, cluster in enumerate(clusters_refine):
        if cluster:  # Only add non-empty clusters
            cluster2id[c_idx] = cluster
            ann_in_cluster.extend(cluster)
    
    # Handle annotations not in any cluster
    if cluster2id:
        clust_id = max(cluster2id.keys()) + 1
    else:
        clust_id = 0
        
    for ann_id in annset_ids:
        if ann_id not in ann_in_cluster:
            cluster2id[int(clust_id)] = [int(ann_id)]
            clust_id += 1
    # create id2cluster
    id2cluster = {}
    for key, values in cluster2id.items():
        for idx in values:
            id2cluster[idx] = key
    # create annotation set
    # build annotation set
    if separate_annset:
        try:
            doc.remove_annset('enitites_clustered')
        except:
            pass
        newset = doc.annset('enitites_clustered')
        for ann in valid_annotations:
            if ann.id in id2cluster:
                newset.add(ann.start, ann.end, f'CLUST-{id2cluster[ann.id]}')
    else:
        for ann in valid_annotations:
            if ann.id in id2cluster:
                annset[ann.id].features['cluster'] = id2cluster[ann.id]

    doc.features['clusters'] = {}
    clusters_info = []
    cl_id=0
    for key, values in cluster2id.items():
        title = []
        types = []
        mentions = []
        if values:
            for idx in values:
                mention = doc.text[annset[idx].start:annset[idx].end].replace('\n',' ')
                title.append(mention)
                types.append(annset[idx].type)
                mentions.append({'id':idx, 'mention':mention})
            most_freq_title = max(set(title), key=title.count)
            most_freq_type = max(set(types), key=types.count)
            clusters_info.append({'title':most_freq_title,'id':cl_id,'type':most_freq_type, 'mentions':mentions})
            cl_id += 1
    doc.features['clusters'][annset_name] = clusters_info

    if not 'pipeline' in doc.features:
        doc.features['pipeline'] = []
    doc.features['pipeline'].append('clustering')

    return doc