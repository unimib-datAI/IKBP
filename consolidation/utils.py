from copy import deepcopy
from collections import defaultdict
from itertools import combinations

def make_nil_url(doc_id, cluster_title, cluster_id):
    # url NIL -> doc_id + cluster_title + cluster_id
    nil_url = doc_id.replace(' ','_') + '/' + cluster_title.replace(' ','_') + \
        '_' + str(cluster_id)
    return nil_url

def consolidate_url_func(mentions, annset, idx_dict, url, title, cluster_id):
    for mention in mentions:
        ann = annset[idx_dict[mention['id']]]
        ann['features']['url'] = url
        ann['features']['title'] = title
        ann['features']['cluster'] = cluster_id

def consolidate_types_func(mentions, annset, idx_dict, type):
    for mention in mentions:
        ann = annset[idx_dict[mention['id']]]
        ann['type'] = type

def merge_cluster(selected_clusters, id, url, annset, idx_dict):
    mentions = []
    types = []
    for cluster in selected_clusters:
        mentions += cluster['mentions']
        types.append(cluster['type'])
    merged_cluster = {'title':cluster['title'], 'id':id, 
                    'type': max(set(types), key = types.count), 
                    'mentions': mentions, 'url':url}
    consolidate_url_func(mentions, annset, idx_dict, url, merged_cluster['title'], merged_cluster['id'])

    return merged_cluster

def del_clusters(clusters, id_to_remove):
    retain_clusters = []
    for cluster in clusters:
        if cluster['id'] not in id_to_remove:
            retain_clusters.append(cluster)
    return retain_clusters

def reset_cluster_index(clusters, idx_dict, annset):
    for id, cluster in enumerate(clusters):
        cluster['id'] = id
        for mention in cluster['mentions']:
            ann = annset[idx_dict[mention['id']]]
            ann['features']['cluster'] = id

def consolidation(doc, annset_name='entities_merged', output_annset_name='entities_consolidated',
                  consolidate_linking=True, consolidate_types=True, merge_same_name=True, merge_similar_name=True):

    doc['annotation_sets'][output_annset_name] = deepcopy(doc['annotation_sets'][annset_name])
    doc['annotation_sets'][output_annset_name]['name'] = output_annset_name
    doc['features']['clusters'][output_annset_name] = deepcopy(doc['features']['clusters'][annset_name])


    clusters = doc['features']['clusters'][output_annset_name]
    annset = doc['annotation_sets'][output_annset_name]['annotations']

    if consolidate_linking:
        # ann_idx 2 list_idx
        idx_dict = {ann['id']:list_idx for list_idx, ann in enumerate(annset)}
        # consolidate url and title between ann in the same cluster
        for cluster in clusters:
            urls = []
            titles = []
            url2title= {}
            for mention in cluster['mentions']:
                ann = annset[idx_dict[mention['id']]]
                url = ann['features']['url']
                mention_span = doc['text'][ann['start']:ann['end']]
                titles.append(mention_span.lower())
                if url:
                    urls.append(url)
                    url2title[url] = ann['features']['title']
                else:
                    urls.append('NIL')
            most_common_url = max(set(urls), key = urls.count)
            longest_title = max(set(titles))
            if most_common_url == 'NIL':
                title = longest_title.title()
                url = make_nil_url(doc['features']['id'], title, cluster['id'])
            else:
                title = url2title[most_common_url]
                url = most_common_url
            cluster['title'] = title
            cluster['url'] = url
            consolidate_url_func(cluster['mentions'], annset, idx_dict, url, title, cluster['id'])

        # merge cluster with the same link
        max_cluster_id = max([cluster['id'] for cluster in clusters])
        url2cluster = defaultdict(list)
        for cluster in clusters:
            url2cluster[cluster['url']].append(cluster['id'])
        id_to_remove = []
        for url, cl_idxs in url2cluster.items():
            if len(cl_idxs) > 1:
                # let's merge
                selected_clusters = []
                for cluster in clusters:
                    if cluster['id'] in cl_idxs:
                        selected_clusters.append(cluster)
                        id_to_remove.append(cluster['id'])
                max_cluster_id += 1
                merged_cluster = merge_cluster(selected_clusters, max_cluster_id, url, annset, idx_dict)
                clusters.append(merged_cluster)

        # del merged cluster
        clusters = del_clusters(clusters, id_to_remove)

    if consolidate_types:
        # ann_idx 2 list_idx
        idx_dict = {ann['id']:list_idx for list_idx, ann in enumerate(annset)}
        # consolidate url and title between ann in the same cluster
        for cluster in clusters:
            types = []
            for mention in cluster['mentions']:
                ann = annset[idx_dict[mention['id']]]
                types.append(ann['type'])
            most_common_type = max(set(types), key=types.count)
            consolidate_types_func(cluster['mentions'], annset,
                                    idx_dict, most_common_type)
            
    if merge_same_name:
        # select "person" type cluster
        # Merge same name i.e. Mario Rossi | Mario Rossi
        max_cluster_id = max([cluster['id'] for cluster in clusters])
        title2cluster = defaultdict(list)
        for cluster in clusters:
            title = cluster['title'].split(' ')
            title.sort()
            title = ' '.join(title)
            title2cluster[title].append(cluster['id'])
        for title, cl_idxs in title2cluster.items():
            if len(cl_idxs) > 1:
                # let's merge
                selected_clusters = []
                for cluster in clusters:
                    if cluster['id'] in cl_idxs:
                        selected_clusters.append(cluster)
                        id_to_remove.append(cluster['id'])
                max_cluster_id += 1
                if 'http' not in selected_clusters[0]['url']:
                    url = make_nil_url(doc['features']['id'], title, max_cluster_id)
                else:
                    url = selected_clusters[0]['url']
                merged_cluster = merge_cluster(selected_clusters, max_cluster_id, url, annset, idx_dict)
                clusters.append(merged_cluster)
        
        # del merged cluster
        clusters = del_clusters(clusters, id_to_remove)

    if merge_similar_name:
        max_cluster_id = max([cluster['id'] for cluster in clusters])
        # i.e. Mario -> Mario Rossi -> only if there aren't other cases such as Mario Bianchi
        person_list_idx = []
        for list_id, cluster in enumerate(clusters):
            if cluster['type'] == 'persona':
                person_list_idx.append(list_id)
        cluster_pairs = combinations(person_list_idx, 2)
        cluster2merge = []
        cluster_selected = []
        cluster_ignore = []
        for pair in cluster_pairs:
            cluster1 = clusters[pair[0]]
            cluster2 = clusters[pair[1]]
            title1 = cluster1['title'].split(' ')
            title2 = cluster2['title'].split(' ')
            title1.sort()
            title2.sort()
            common_words = list(set(title1) & set(title2))
            if len(common_words) >= 1:
                if cluster1['id'] not in cluster_selected and cluster2['id'] not in cluster_selected:
                    cluster2merge.append([cluster1['id'], cluster2['id']])
                    cluster_selected += [cluster1['id'], cluster2['id']]
                else:
                    cluster_ignore += [cluster1['id'], cluster2['id']]
        # merge cluster
        id_to_remove = []
        for pair in cluster2merge:
            if pair[0] not in cluster_ignore and pair[1] not in cluster_ignore:
                selected_clusters = []
                for cluster in clusters:
                    if cluster['id'] in pair:
                        selected_clusters.append(cluster)
                        id_to_remove.append(cluster['id'])
                titles = []
                for cluster in selected_clusters:
                    titles.append(cluster['title'])
                title = max(titles)        
                max_cluster_id += 1
                if 'http' not in selected_clusters[0]['url']:
                    url = make_nil_url(doc['features']['id'], title, max_cluster_id)
                else:
                    url = selected_clusters[0]['url']
                merged_cluster = merge_cluster(selected_clusters, max_cluster_id, url, annset, idx_dict)
                clusters.append(merged_cluster)

        # del merged cluster
        clusters = del_clusters(clusters, id_to_remove)       

    mentions_ids = []
    for cluster in clusters:
        for mention in cluster['mentions']:
            mentions_ids.append(mention['id'])

    return doc