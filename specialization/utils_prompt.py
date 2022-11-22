from gatenlp import Document
import numpy as np
import json
from transformers import AutoModelForMaskedLM , AutoTokenizer
import torch
import itertools
import pandas as pd
from torch import nn
import torch.nn.functional as F
from imblearn.ensemble import BalancedRandomForestClassifier


def import_document(doc_path):
    ''' import document from Giustizia App '''
    # load document
    with open(doc_path, 'r') as fd:
        dizionario = json.load(fd)
    # id to int
    for annset in dizionario['annotation_sets']:
        for i, annotation in enumerate(dizionario['annotation_sets'][annset]['annotations']):
            dizionario['annotation_sets'][annset]['annotations'][i]['id'] = int(annotation['id'])
    doc = Document.from_dict(dizionario)
    return doc


def get_annotated_example(doc, annotation_set, type_id, span=50, doc_id=None):
    ''' get annotated example from gatenlp document
    
    Args:
    doc: gatenlp document
    annotation_set: name of annotation_set 
    span:   number of character (left and right) to include into mention context
    id: id of document
    
    Returns:
    example_list:   a dictionary with mention, its label, its context, its offset, 
                    its aaotation id and document id
    labels: a list with typing labels in document
    '''
    # get text
    text = doc.text
    # iterate over annotation
    example_list = [] # save example here
    labels = [] # save unique labels
    for ann in doc.annset(annotation_set):
        mention = ann.features['mention'].replace('\n', ' ') # get mention
        mention_type = ann.type # get label
        other_types = []
        if 'types' in ann.features:
            other_types = ann.features['types']
        if mention_type not in labels:
            labels.append(mention_type)
        mention_start = ann.start
        mention_end = ann.end
        # get context
        context_start = np.where(mention_start-span>= 0, mention_start-span, 0)
        context_end = np.where(mention_end+span <= len(text), mention_end+span, len(text))
        context = text[context_start:context_end]
        context = context.replace('\n', ' ') # del usless \n
        # crop first and last word cause they could be truncated
        # only if the mention isn't at the beginning or at the end of the doc
        if mention_start != 0 and mention_end != len(text):
            first_space = context.find(' ')
            last_space = context.rfind(' ')
            context_clean = context[first_space+1:last_space]
            context_start = int(context_start + first_space+1)
            context_end = context_start + len(context_clean)
        # mention at the beginning of doc
        elif mention_start == 0 and mention_end != len(text):
            first_space = -1
            last_space = context.rfind(' ')
            context_clean = context[first_space+1:last_space]
            context_start = int(context_start + first_space+1)
            context_end = context_start + len(context_clean)
        # mention at the end of doc
        elif mention_start != 0 and mention_end == len(text):
            first_space = context.find(' ')
            last_space = len(context) + 1
            context_clean = context[first_space+1:last_space]
            context_start = int(context_start + first_space+1)
            context_end = context_start + len(context_clean)       
            
        # save in a dictionary
        all_types = set.union(set(mention_type), set(other_types))
        if type_id in all_types:
            example = {'mention':mention, 'mention_type':type_id, 'text':context_clean, 
                    'offset_doc_start':mention_start, 'offset_doc_end':mention_end, 
                    'offset_ex_start':mention_start-context_start,
                    'offset_ex_end':mention_start-context_start+len(mention),
                    'doc_id': doc_id, 'id':ann.id}
            example_list.append(example)
        
    return (example_list, labels)



class Prompting(object):
    def __init__(self, model_name):
        # define model and tokenizer from HF
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def prompt_prediction(self, ann_example, template, softmax=False):
        ''' Predict [MASK] token in prompt

        Args:
        ann_example: A dictionary with a mention and its context
        template: Template of prompt to add to the end of context, containg [MASK] token
        softmax: if True, apply a softmax on prediction (all BERT vocabulary)

        Returns:
        mask_pred: A tensor containg the prediction for the [MASK] token.

        '''
        # build prompt
        prompt = template.format(mention=ann_example['mention'])
        # generate example
        text = ann_example['text'] + '. ' + prompt
        indexed_tokens = self.tokenizer(text, return_tensors="pt").input_ids
        tokenized_text = self.tokenizer.convert_ids_to_tokens(indexed_tokens[0])
        # take the first masked token
        mask_pos = tokenized_text.index(self.tokenizer.mask_token)
        # predict masked token
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(indexed_tokens)
            predictions = outputs[0]
        mask_pred = predictions[0, mask_pos]
        if softmax:
            mask_pred = torch.nn.functional.softmax(mask_pred, dim=0)
        return mask_pred

    def examples_prediction(self, examples, template, softmax=False):
        ''' Predict [MASK] token for each example in a list
        
        Args:
        examples:   List of examples (i.e. dict with a mention and its context)
        template:   Template of prompt to add to the end of context, containg [MASK] token
        softmax:    If True, apply a softmax on prediction (all BERT vocabulary)
        
        Returns:
        X:  2D torch tensor with predictions for the [MASK] token
        '''
        X = [self.prompt_prediction(example, template, softmax=softmax) for example in examples]
        X = torch.stack(X, dim=0)
        return X        

def verbalizer_to_index(verbalizer, tokenizer):
    verbalizer_idx = {}
    for label in verbalizer.keys():
        verbalizer_idx[label] = tokenizer.convert_tokens_to_ids(verbalizer[label])
    return verbalizer_idx

def filter_masked(X, verbalizer, tokenizer):
    # get verbalizer token idx
    verb_idx = verbalizer_to_index(verbalizer, tokenizer)
    filter_idx = list(itertools.chain(*verb_idx.values()))
    # filter prediction
    X_filter = torch.index_select(X, 1, torch.tensor(filter_idx))
    return X_filter

class VanillaClf(object):
    def __init__(self):
        pass
    
    def predict_proba(self, X, verbalizer, tokenizer, summarize='mean', logits=True, k=5):
        ''' Compute posterior probability for each type
        
        Args:
        X:  2D torch tensor with [MASK] logits/probabilites for every terms in BERT vocabulary
        verbalizer: A dict with a list of key-words in BERT vocabulary related to types
        tokenizer:  Tokenizer of BERT model from HF
        summarize:  Method to summarize probabilites between each types
        logits: if True, a softmax is applicated to logits filtered by the verbalizer
        
        Returns:
        summary_df: A Pandas DataFrame with the final posterior proabilites for every observations  
        
        '''
        # filter input
        X_filter = filter_masked(X, verbalizer, tokenizer)
        # apply softmax if inputs are logits
        if logits:
            X_filter = torch.nn.functional.softmax(X_filter, dim=1)
        # convert to pandas df
        X_filter_df = pd.DataFrame(X_filter.numpy())
        # verbalizer token as columns names
        verb_name = list(itertools.chain(*verbalizer.values()))
        X_filter_df.columns = verb_name
        # compute stratified summarization
        summary_list = []
        for label in verbalizer.keys():
            # filter token realted to single label
            df_label = X_filter_df[verbalizer[label]]
            # summarize method
            if summarize=='mean':
                label_mean = df_label.mean(axis=1).to_numpy()
                summary_list.append(label_mean)
            elif summarize=='sum':
                label_sum = df_label.sum(axis=1).to_numpy()
                summary_list.append(label_sum)
            elif summarize=='sum_square':
                df_label_square = df_label**2
                label_sum = df_label_square.sum(axis=1).to_numpy()
                summary_list.append(label_sum)
            elif summarize=='max':
                label_max = df_label.max(axis=1).to_numpy()
                summary_list.append(label_max)
            elif summarize=='top_k':
                df_label_numpy = df_label.to_numpy()
                top_values = np.sort(df_label_numpy, axis=1)[:,-k:]
                summary_list.append(top_values.mean(axis=1))
        summary_list = np.array(summary_list).T
        summary_df = pd.DataFrame(summary_list, columns=verbalizer.keys())
        return summary_df
    
    def predict(self, X, verbalizer, tokenizer, summarize='mean', logits=True):
        ''' Predict for every observations the type with the highest posterior proability
        
        Args:
        X:  2D torch tensor with [MASK] logits/probabilites for every terms in BERT vocabulary
        verbalizer: A dict with a list of key-words in BERT vocabulary related to types
        tokenizer:  Tokenizer of BERT model from HF
        summarize:  Method to summarize probabilites between each types
        logits: if True, a softmax is applicated to logits filtered by the verbalizer
        
        Returns:
        pred_df: A numpy array with the type predicted for every observations  
        
        '''
        pred_df = self.predict_proba(X, verbalizer, tokenizer, summarize, logits)
        return pred_df.idxmax(axis=1).to_numpy()


class BalancedRandomForestPrompt(BalancedRandomForestClassifier):
    def prompt_fit(self, X_train, y_train, verbalizer, tokenizer, logits=True):
        X_train = filter_masked(X_train, verbalizer, tokenizer)
        if logits:
            X_train = torch.nn.functional.softmax(X_train, dim=1)
        return self.fit(X_train, y_train)
    def prompt_predict(self, X_test, verbalizer, tokenizer, logits=True):
        X_test = filter_masked(X_test, verbalizer, tokenizer)
        if logits:
            X_test = torch.nn.functional.softmax(X_test, dim=1)
        return self.predict(X_test)    