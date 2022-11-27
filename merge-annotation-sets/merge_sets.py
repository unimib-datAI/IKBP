from collections import Counter
from itertools import groupby
import logging

class MyAnnotation:
  def __init__(self, start, end, length, ann_type, root_type, text, source):
    self.start = start
    self.end = end
    self.length = length
    self.ann_type = ann_type
    self.root_type = root_type
    self.text = text
    self.source = source

  def __repr__(self):
    """
    String representation of the annotation.
    """
    return "MyAnnotation({},{},{},{},{},{},{})".format(
        self.start, self.end, self.length, self.ann_type, self.root_type, self.text, self.source
        )

  def is_equal(self, other_ann, exclude=[]) -> bool:
    if (self.start == other_ann.start or 'start' in exclude)\
      and (self.end == other_ann.end or 'end' in exclude)\
      and (self.length == other_ann.length or 'length' in exclude)\
      and (self.ann_type == other_ann.ann_type or 'ann_type' in exclude)\
    and (self.source == other_ann.source or 'source' in exclude):
      return True
    else:
      return False

  def is_in(self, ann_list, exclude=[]) -> bool:
    if any([self.is_equal(ann, exclude=exclude) for ann in ann_list]):
      return True
    else:
      return False

  def type_is_related(self, other_ann, type_relation_df):
    df_01 = type_relation_df[(type_relation_df == self.type).any(axis=1)] #filter by self.type
    df_02 = df_01[(df_01 == other_ann.type).any(axis=1)] #filter df again by other_ann.type
    if df_02.empty:
      return False
    else:
      return True

def is_overlapping(item_1, item_2):
    return item_1.start == item_2.start and item_1.end == item_2.end

def normalize_entity(ann_type):
  if ann_type.lower() in ['person']:
    return ann_type[:3]
  else:
    return ann_type


def get_root_type(ann, annset, type_relation_df):
  #try:
  #  return entity_db[entity_db['type'] == ann_type.lower()]['root_type'].iloc[0].upper()
  #except:
  #  return ann_type.upper()

  # check annotations fully overlapped from the same source and then check relation_df in column "role" and write column "type"
  # I stop at the first matched other_ann, because in a group of fully overlapped annotations from the same source, only one can be the root_type
  for other_ann in annset:
    if is_overlapping(ann, other_ann):
      temp_df = type_relation_df[type_relation_df['type']==normalize_entity(ann.type)][type_relation_df['root_type']==normalize_entity(other_ann.type)]
      if temp_df.empty:
        return normalize_entity(ann.type)
      else:
        if len(temp_df['root_type']) > 1:
          logging.warning('multiple root type')
        return temp_df['root_type'].iloc[0]



def preprocess_annset(doc, annset_exclusion_list, types_list, type_relation_df):
  # selected annset
  selected_annset_names = [annset_name for annset_name in doc.annset_names() if annset_name not in annset_exclusion_list]

  myannotation_list = []
  for annset_name in selected_annset_names:
    myannotation_temp_list = [
        MyAnnotation(
            ann.start,
            ann.end,
            ann.end - ann.start,
            normalize_entity(ann.type),
            get_root_type(ann, doc.anns(annset_name), type_relation_df),
            doc.text[ann.start:ann.end],
            source = annset_name
            )
        for ann in doc.anns(annset_name) if ann.type in types_list]
    myannotation_list.extend(myannotation_temp_list)
  ordered_myannotation_list = [annotation for annotation in sorted(myannotation_list, key=lambda ann: (ann.start, ann.end, ann.ann_type))]
  return ordered_myannotation_list


def analyze_overlap(annotation_set_input):
    annotation_set = annotation_set_input.copy()
    current_element = None
    partial_intervals = []
    overlap_intervals = []
    disjoint_intervals = []
    while annotation_set:
        current_element = annotation_set.pop(0)

        if not annotation_set:
            disjoint_intervals.append(current_element)

        elif is_partial(current_element, annotation_set[0]):
            current_partial = [current_element]
            current_partial.extend(extract_partial(current_element, annotation_set))
            partial_intervals.append(current_partial)

        elif is_overlapping(current_element, annotation_set[0]):
            current_interval = [current_element]
            while annotation_set and is_overlapping(current_element, annotation_set[0]):
                current_interval.append(annotation_set.pop(0))
            if annotation_set and is_partial(current_element, annotation_set[0]):
                current_interval.extend(extract_partial(current_element, annotation_set))
                partial_intervals.append(current_interval)
            else:
                overlap_intervals.append(current_interval)

        else:
            disjoint_intervals.append(current_element)

    return partial_intervals, overlap_intervals, disjoint_intervals


def extract_partial(current_element, annotation_set):
    current_partial = []
    while annotation_set and is_partial(current_element, annotation_set[0]):
        current_partial.append(annotation_set.pop(0))
    return current_partial


def is_disjoint(item_1, item_2):
  # TODO reason about <=; we are using gatenlp with python-style offsets (end not included)
    return item_1.end <= item_2.start or item_2.end <= item_1.start


def is_overlapping(item_1, item_2):
    return item_1.start == item_2.start and item_1.end == item_2.end


def is_partial(item_1, item_2):
    return not is_disjoint(item_1, item_2) and not is_overlapping(item_1, item_2)

def get_unique_ann(ann_list_input, best_ner_name):
  '''
  Get a list of unique annotations. Annotations are equal if all their
  attributes are equal except for source.
  '''
  ann_list = ann_list_input.copy()
  unique_ann_list = []
  while ann_list:
    ann = ann_list.pop(0)
    if ann.is_in(ann_list, exclude='source'):
      pass
    else:
      unique_ann_list.append(ann)
  unique_ann_list = [MyAnnotation(x.start, x.end, x.length, x.ann_type, x.root_type, x.text, best_ner_name) for x in unique_ann_list]
  return unique_ann_list

def all_related(ann_list, relation_db):
  for current_ann in ann_list:
    if not all([current_ann.type_is_related(ann, relation_db) for ann in ann_list]):
      return False
  return True

def check_annset_priority(ann_list, annset_priority):
  # check if a single max priority annset exists
  reduced_annset_priority = {key: val for key, val in annset_priority.items() if key in [x.source for x in ann_list]}
  max_value = max([val for key, val in reduced_annset_priority.items()])
  reduced_annset_max_priority = [key for key, val in reduced_annset_priority.items() if val==max_value]

  if len(reduced_annset_max_priority) == 1:
    return reduced_annset_max_priority[0]
  else:
    return None

def check_root_type(ann_list, annset_priority) -> list:
  '''
  Return integer, root type filter. Return 1 if all types equal, 2 if
  root_types different, but prevalent root_type exists, 3 if root_types
  different and prevalent root_type does not exist, but metadata source exists
  and it is chosen and root_type is unique, 4 if root_types
  different and prevalent root_type does not exist, but metadata source exists
  and it is chosen, but root_type is unique, 5 if root_types are different and
  prevalent root_type does not exist and metadata source does not exist. All
  sources are kept.
  '''

  # weight the frequencies by the annset priorty
  root_type_Counter = {}
  for ann in ann_list:
    if ann.root_type not in root_type_Counter:
      root_type_Counter[ann.root_type] = 0
    root_type_Counter[ann.root_type] += int(annset_priority.get(ann.source, 1))
  root_type_Counter = Counter(root_type_Counter)

  most_frequent_type = root_type_Counter.most_common(1)[0][0]

  local_annset_priority = check_annset_priority(ann_list, annset_priority)
  filtered_list = [x for x in ann_list if x.source == local_annset_priority]
  filtered_root_type_Counter = Counter([x.root_type for x in filtered_list])

  # 1) root_types all equal
  if len(root_type_Counter.most_common()) == 1: # there is only one group

    return 1, [most_frequent_type]

  # 2) root_types different, but prevalent root_type exists
  elif root_type_Counter.most_common(2)[0][1] > root_type_Counter.most_common(2)[1][1]: # there is no tie in the most common root_type

    return 2, [most_frequent_type]

  # 3) root_types different and prevalent root_type does not exist, but metadata
  #    source exists and it is chosen and root_type is unique
  elif local_annset_priority\
  and len(list(filtered_root_type_Counter)) == 1:

    return 3, list(filtered_root_type_Counter)

  # 4) as per 3, but metadata source root_type is not unique
  elif local_annset_priority:
    logging.warning('metadata source has multiple root type')
    return 4, list(filtered_root_type_Counter)

  # 5) root_types different and prevalent root_type does not exist and metadata
  #    source does not exist
  else:
    return 5, list(root_type_Counter)  #return unique elements

def reduce_disjoints(disjoints, best_ner_name):
  return [MyAnnotation(ann.start, ann.end, ann.length, ann.ann_type, ann.root_type, ann.text, best_ner_name) for ann in disjoints]

def reduce_overlaps(overlaps, best_ner_name, annset_priority):
  cleaned_overlap_list = []

  for ann_list in overlaps:
    type_analysis_result, root_type_filter = check_root_type(ann_list, annset_priority)

    #print(type_analysis_result) # Keep for debug
    filtered_list = [x for x in ann_list if x.root_type in root_type_filter] # Filter ann_list by type analysis result
    cleaned_overlap_list.extend(get_unique_ann(filtered_list, best_ner_name))  # remove duplicates

  return cleaned_overlap_list

def inner_reduce_partial_overlaps(ann_list, best_ner_name, annset_priority, maximum_per_parts, maximum_parts):
  type_analysis_result, root_type_filter = check_root_type(ann_list, annset_priority)
  # print(type_analysis_result, root_type_filter) # keep for debug

  # if type analysis is possible and root_type is PER
  if type_analysis_result != 4 and 'PER' in root_type_filter:
    current_maximum_parts = maximum_per_parts # set proper maximum n° of parts if PER
  else:
    current_maximum_parts = maximum_parts # set proper maximum n° of parts

  # keep only root_type_filter (no filter if type analysis is not possible) with n° of parts <= current_maximum_parts and sort desc
  sorted_filtered_list = [annotation for annotation
                          in sorted(ann_list,
                                    reverse=True,
                                    key=lambda ann: ann.length)
                          if annotation.root_type in root_type_filter
                          and len(annotation.text.split()) <= current_maximum_parts]

  # filter by maximum_length
  maximum_length = sorted_filtered_list[0].length
  longest_ann_list = [ann for ann in sorted_filtered_list if ann.length == maximum_length]

  return type_analysis_result, longest_ann_list

def reduce_partial_overlaps(partial_overlaps, best_ner_name, annset_priority, maximum_per_parts, maximum_parts):
  # 1) check if same root_type
  #     if not check majority or metadata
  #       if majority or metadata is possible goto 2)
  #       else keep longest with a failsafe (maximum_parts)
  #     if yes goto 2)
  # 2) check if root_type is person
  #     if not keep longest with a failsafe (maximum_parts)
  #     if yes keep longest of ann with n° of parts <= maximum_per_parts
  cleaned_partial_overlap_list = []

  for ann_list in partial_overlaps:
    type_analysis_result, longest_ann_list = inner_reduce_partial_overlaps(ann_list, best_ner_name, annset_priority, maximum_per_parts, maximum_parts)
    # print(longest_ann_list) # keep for debug

    # if type analysis is not possible on original ann_list, do it again on longest_ann_list.
    # Having a different n° of annotations, results may be different
    # worst case scenario, all longest results are kept
    if type_analysis_result == 4:
      longest_ann_list = inner_reduce_partial_overlaps(longest_ann_list, best_ner_name, annset_priority, maximum_per_parts, maximum_parts)[1]

    # remove duplicates
    cleaned_partial_overlap_list.extend(get_unique_ann(longest_ann_list, best_ner_name)) # may contain more than one element (e.g. GIUDICE e PER)

  return cleaned_partial_overlap_list

def create_best_NER_annset(doc, annset_exclusion_list, types_list, best_ner_name, type_relation_df, annset_priority, maximum_per_parts, maximum_parts):
  ordered_myannotation_list = preprocess_annset(doc, annset_exclusion_list, types_list, type_relation_df)
  partial_overlaps, overlaps, disjoints = analyze_overlap(ordered_myannotation_list)
  best_NER_list = []
  best_NER_list.extend(reduce_disjoints(disjoints, best_ner_name))
  best_NER_list.extend(reduce_overlaps(overlaps, best_ner_name, annset_priority))
  best_NER_list.extend(reduce_partial_overlaps(partial_overlaps, best_ner_name, annset_priority, maximum_per_parts, maximum_parts))

  try:
      doc.annset(best_ner_name).clear()
  except:
    pass
  annset = doc.annset(best_ner_name)

  for ent in best_NER_list:
    feat_to_add = {
      "mention": doc.text[ent.start:ent.end],
      "types": [ent.ann_type],
      "ner": {
        "type": ent.ann_type,
        "source": "mergener",
        }}
    if ent.ann_type == 'DATE':
      feat_to_add['linking'] = {
          "skip": True
      }
    annset.add(ent.start, ent.end, ent.ann_type, feat_to_add)
  return doc