import sys
sys.path.insert(1, './trie-search')

import itertools
from tqdm import tqdm
import trie_search
import os
import pickle
import re
import string

class TrieNER:
    def __init__(self, path = None):
        # trie structure holding the patterns to find
        self.trie = None
        self.last_id = 0
        # kb
        self.entities = dict()
        self.unique_entities = set()
        # reference to patterns and original string
        self.patterns = dict()
        # regex used to clean text when finding matches
        self.clean_regex = '|'.join([re.escape(char) for char in [*string.punctuation, '\n']])
        
        if path is not None:
            self.load(path)
    
    def __get_entities_from_pattern(self, pattern):
        entity_ids = self.patterns[pattern]['ids']
        entities = [self.entities[entity_id] for entity_id in entity_ids]
        return entities
    
    def __permutations(self, items):
        result = []
        for i in range(1, len(items) + 1):
            for comb in itertools.permutations(items, i):
                result.append(' '.join(comb))
        return result
    
    def __add_entity(self, key, entity_type, entity_id):
        if key not in self.unique_entities:
            self.entities[entity_id] = { 'id': entity_id, 'name': key, 'type': entity_type }
            self.unique_entities.add(key)
            return True
        return False
            
    def __add_pattern(self, key, entity_id):
        if key in self.patterns:
            self.patterns[key]['ids'].append(entity_id)
        else:
            self.patterns[key] = { 'ids': [entity_id] }
    
    def __add_hyphen_patterns(self, item, entity_id):
      item = item.lower()
      if re.match("\w+-\w+", item):
        self.__add_pattern(item.replace(' - ', '-'), entity_id)
      else:
        self.__add_pattern(item.replace('-', ' - '), entity_id)
      
      item_hyphenless = " ".join(item.replace('-', ' ').split())

      for token in self.__permutations(item_hyphenless.split()):
        self.__add_pattern(token, entity_id)
    
    def __create_annotation(self, ann_id, start, end, pattern):
        entities = self.__get_entities_from_pattern(pattern)
        types = list(set([entity['type'] for entity in entities]))
        return {
            'id': ann_id,
            'start': start,
            'end': end,
            'type': types[0],
            'features': {
                'mention': pattern,
                'types': types[1:],
                'entities': entities
            }
        }
    
    """
    Save trie and kb objects
    """
    def save(self, path = './kb'):
        if not os.path.isdir(path):
            os.mkdir(path)
        with open(os.path.join(path,'kb.entities'), 'wb') as handle:
            pickle.dump(self.entities, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open(os.path.join(path,'kb.unique_entities'), 'wb') as handle:
            pickle.dump(self.unique_entities, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open(os.path.join(path,'kb.patterns'), 'wb') as handle:
            pickle.dump(self.patterns, handle, protocol=pickle.HIGHEST_PROTOCOL)
        if self.trie is not None:
            self.trie.save(os.path.join(path,'kb.trie'))
    """
    Load trie and kb objects
    """
    def load(self, path_to_folder = './kb'):
        with open(os.path.join(path_to_folder,'kb.entities'), 'rb') as handle:
            self.entities = pickle.load(handle)
            self.last_id = list(self.entities.keys())[-1]
        with open(os.path.join(path_to_folder,'kb.unique_entities'), 'rb') as handle:
            self.unique_entities = pickle.load(handle)
        with open(os.path.join(path_to_folder,'kb.patterns'), 'rb') as handle:
            self.patterns = pickle.load(handle)
        self.trie = trie_search.TrieSearch(filepath = os.path.join(path_to_folder,'kb.trie'))
    
    """
    Get kb entities
    """
    def get_entities(self):
        return self.entities
    
    """
    Get patterns used to identify entities of the kb
    """
    def get_patterns(self):
        return self.patterns
    
    """
    Add entities to the kb. It automatically creates patterns to identify in the text.
    """
    def add_entities(self, items, entity_type, permutations = True):
        for item in tqdm(items):
            entity_id = self.last_id + 1
            self.last_id += 1
            # item = item.replace(' - ', '-')
            added = self.__add_entity(item, entity_type, entity_id)
            if added:
              # item = item.replace(' - ', ' ')
              item = re.sub(self.clean_regex, " ", item)
              self.__add_pattern(item.lower(), entity_id)
              
              if permutations:
                # if '-' in item:
                #   self.__add_hyphen_patterns(item, entity_id)
                # else:
                for token in self.__permutations(item.split()):
                  self.__add_pattern(token.lower(), entity_id)
              # else:
              #   self.__add_pattern(item.lower(), entity_id)
              self.create_trie()
    
    """
    Create trie data structure useing the patterns to identify entities of the kb
    """
    def create_trie(self):
        if len(self.patterns) == 0:
            raise Exception("There are no patterns to create the trie structure with. Make sure to add some entities first.")
        patterns = list(self.patterns.keys())
        self.trie = trie_search.TrieSearch(self.patterns)
    
    """
    Find entity matches using the trie
    """
    def find_matches(self, text):
        match_groups = dict()
        text = re.sub(self.clean_regex, " ", text)
        for pattern, start_idx in sorted(self.trie.search_longest_patterns(text.lower()), key=lambda x: x[1]):
          if start_idx not in match_groups:
              match_groups[start_idx] = [pattern]
          else:
              match_groups[start_idx].append(pattern)

        annotations = []
    
        if len(match_groups) > 0:
            ann_id = 0
            start_offsets = sorted(list(match_groups.keys()))
            for index, start in enumerate(start_offsets):
                pattern = max(match_groups[start], key=len)
                end = start + len(pattern)
                
                annotation = self.__create_annotation(ann_id + 1, start, end, pattern)
                
                if len(annotations) == 0:
                    annotations.append(annotation)
                    ann_id += 1
                else:
                    prev_ann = annotations[ann_id - 1]
                    if start > prev_ann['end']:
                        annotations.append(annotation)
                        ann_id += 1
                
        return annotations

        