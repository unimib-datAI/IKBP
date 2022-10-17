import json

def resolve_annotations(ann_set):
  annotations = ann_set['annotations']

  new_annotations = []

  n_conflicts = 0

  for i, ann in enumerate(annotations):
    if i == 0:
      new_annotations.append(ann)
    else:
      prev_ann = new_annotations[i - 1]

      if prev_ann['start'] == ann['start'] and prev_ann['end'] == ann['end']:
        # do something
        if prev_ann['type'] != ann['type']:
          types = set()

          if 'types' in prev_ann['features']:
            types = set(prev_ann['features']['types'])

          if ann['type'] not in types:
            n_conflicts += 1
            print(f'''
              Found conflict with previous annotation with types: {list(types)}
              And the new annotation with type: {ann['type']}
            ''')

            print('''
              - [a] ADD new type
              - [b] DISCARD new type
              - [c] REPLACE all current types with new type
            ''')


            while True:
              c = input()

              if c == 'a':
                types.add(ann['type'])
                types_list = list(types)
                new_annotations[i - 1]['type'] = types_list[0]
                new_annotations['features']['types'] = types_list[1:]
                break
              elif c == 'b':
                break
              elif c == 'c':
                types = set([ann['type']])
                types_list = list(types)
                new_annotations[i - 1]['type'] = types_list[0]
                new_annotations['features']['types'] = types_list[1:]
                break
              else:
                print('invalid option')
      else:
        new_annotations.append(ann)

  if n_conflicts > 0:
    ann_set['annotations'] = new_annotations

  print(f'''Resolved {n_conflicts} conflicts''')

  return ann_set

def resolve_conflicts(doc):
  ann_sets = doc['annotation_sets']

  for ann_set_key in ann_sets:
    print('Resolve conflicts for ' + ann_set_key + '? [y]/[n]')
    while True:
      c = input()

      if c == 'y':
        ann_sets[ann_set_key] = resolve_annotations(ann_sets[ann_set_key])
        break
      else:
        print('invalid option')



if __name__ == "__main__":
  with open('./data/test.json') as json_file:
    doc = json.load(json_file)
    resolve_conflicts(doc)