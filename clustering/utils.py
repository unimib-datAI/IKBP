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

def compute_similarity(idx_a, idx_b, text_a, text_b, matr_embd, decimal='', uncased=True):
    if uncased:
        text_a = text_a.lower()
        text_b = text_b.lower()
    embd_a = matr_embd[idx_a]
    embd_b = matr_embd[idx_b]
    score = sourface_similarity(text_a, text_b) + [cosine_similarity(embd_a, embd_b)]
    if decimal:
        score = [round(s, decimal) for s in score]
    return score

def make_clusters(doc_dict, model, annset_name='entities_merged', threshold=0.64, seed=11, separate_annset=False):
    doc = Document.from_dict(doc_dict)
    annset = doc.annset(annset_name)
    matr_embd = np.array([vector_decode(ann.features['linking']['encoding']) for ann in annset])
    annset_ids = [a.id for a in annset]
    pairs = np.array(list(itertools.combinations(annset_ids, 2)))
    # compute similarity
    X_test=[]
    for idx_a, idx_b in pairs:
        text_a = doc.text[annset[idx_a].start:annset[idx_a].end]
        text_b = doc.text[annset[idx_b].start:annset[idx_b].end]
        X_test.append(compute_similarity(idx_a, idx_b, text_a, text_b, matr_embd, 5, uncased=True))
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
        cluster2id[c_idx] = cluster
        ann_in_cluster.extend(cluster)
    prev_max = max(cluster2id.keys()) if len(cluster2id) > 0 else 0
    clust_id = prev_max + 1
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
        for ann in annset:
            newset.add(ann.start, ann.end, f'CLUST-{id2cluster[ann.id]}')
    else:
        for ann in annset:
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