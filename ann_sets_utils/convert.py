def remove_keys(obj):
  keys_to_remove = ['docId', '__v', '_id', 'annotationSetId']
  for key in keys_to_remove:
    if key in obj:
      del obj[key]
  return obj

def split_types_to_annotations(annotation_set):
  annotation_set = remove_keys(annotation_set)

  annotations = []
  ann_id = 1
  for annotation in annotation_set['annotations']:
    annotation = remove_keys(annotation)
    annotation['id'] = ann_id
    ann_id += 1
    annotations.append(annotation)

    if 'types' in annotation['features']:
      for ann_type in annotation['features']['types']:
        ann_copy = annotation.copy()
        ann_copy['type'] = ann_type
        ann_copy['id'] = ann_id
        ann_id += 1
        annotations.append(ann_copy)
  
  annotation_set['annotations'] = annotations
  annotation_set['next_annid'] = ann_id

  return annotation_set


def filter_annotations(annotation_set, types):
  if len(types) == 0:
    return annotation_set

  types_set = set(types)
  annotations = annotation_set['annotations']
  filtered_annotations = list(filter(lambda annotation: annotation['type'] in types_set, annotations))
  annotation_set['annotations'] = filtered_annotations

  return annotation_set



##### EXAMPLE
with open('test.json') as json_file:
    data = json.load(json_file)

    test = split_types_to_annotations(data)
    types_to_filter = ['LOC', 'PER']
    test = filter_annotations(test, types_to_filter)

    print(test)