from gatenlp import Document
import numpy as np

def provv_type(txt):
    # return type of legal document within ['sentenza', 'ordinanza', 'decreto']
    sent_idx = txt.lower().find('sentenza')
    ord_idx = txt.lower().find('ordinanza')
    dec_idx = txt.lower().find('decreto')

    tipi = ['sentenza', 'ordinanza', 'decreto']
    
    adj = lambda x: 10000 if x < 0 else x

    min_tipo = tipi[np.argmin([adj(sent_idx), adj(ord_idx), adj(dec_idx)])]
    min_idx = min(adj(sent_idx), adj(ord_idx), adj(dec_idx))

    if min_idx == 10000:
        return 'altro'
    elif min_tipo == 'sentenza':
        if min_idx / len(txt) > 0.5:
            return 'altro'
        else:
            return 'sentenza'
    else:
        return min_tipo
    
def split_doc(doc, exprs, right_idx=0, left_indx=None, how='min', side='right', strong_match=False):
    # get cut index by regular expression
    exprs = sorted(exprs, key=lambda x: len(x), reverse=True)

    if not left_indx:
        left_indx = len(doc['text'])
    txt = doc['text'][right_idx: left_indx]

    matches = np.array([txt.lower().find(expr) for expr in exprs])

    if how == 'min':
        fun = lambda x: min(x)
        argfun = lambda x: np.argmin(x)
    elif how == 'max':
        fun = lambda x: max(x)
        argfun = lambda x: np.argmax(x)
    else:
        raise Exception('Method not recognized!')

    if matches.sum() == -len(exprs):
        if strong_match:
            raise Exception('No match found!')
        if side == 'right':
            idx = 0
            shift = 0
        else:
            idx = len(txt)
            shift = 0
    else:
        idx = fun(np.where(matches > 0, matches, np.inf)) # adjust for max!
        arg_idx = argfun(np.where(matches > 0, matches, np.inf))
        shift = len(exprs[arg_idx])
    
    if side == 'right':
        return int(right_idx + idx+ shift), left_indx
    else:
        return right_idx, int(right_idx + idx)

def rulebased_interessati(doc, annset_name='entities_merged'):

    doc = Document.from_dict(doc)
    doc_type = provv_type(doc.text)
    doc.features['type'] = doc_type
    doc = doc.to_dict()

    if doc_type == 'sentenza':
        trigger_1 = ['dispositivo di sentenza']
        trigger_2 = ['promossa da:', 'promoss', 'vertente', 'tra ', 'tra\n', 't r a', 'd a', 'da\n', 'parti e conclusioni']
        trigger_3 = ['convenut', 'dispositivo', 'conclusion', 'fatto e diritto', 'fatto ed in diritto', 'fatto e in diritto', 'fatto e di diritto', 
                    'motivi della decisione', 'intervenuto per legge', 'domande della', 'domanda congiunta', 'svolgimento']

        parte_trigger = ['tutti', 'in persona', 'con il', 'con sede', 'rappresentat', 'nata ', 'nato ', 'parte', 'elettivamente', 'rapp.to', 'rapp.']

        controparte_trigger_right = ['\ne\n', 'attori', 'contro', 'confronti di', 'opposta:', 'opponentie', 'attoree', 'e divorzio']
        controparte_trigger_left = ['tutti', 'in persona', 'con il', 'con sede', 'rappresentat', 'nata ', 'nato ', 'parte', 'elettivamente', 'rapp.to', 'rapp.']

        # cut document to focus on intresting text portion
        cut_split = split_doc(doc, trigger_1)
        cut_split = split_doc(doc, trigger_2, right_idx=cut_split[0], left_indx=cut_split[1])
        cut_split = split_doc(doc, trigger_3, right_idx=cut_split[0], left_indx=cut_split[1], side='left')

        # get span where mentions inside are "parte"
        cut_parte = split_doc(doc, parte_trigger, right_idx=cut_split[0], left_indx=cut_split[1], side='left')

        # get span where mentions inside are "controparte"
        cut_controparte = split_doc(doc, controparte_trigger_right, right_idx=cut_split[0], left_indx=cut_split[1])
        cut_controparte = split_doc(doc, controparte_trigger_left, right_idx=cut_controparte[0], left_indx=cut_controparte[1], side='left')

        doc = Document.from_dict(doc)
        annset = doc.annset(annset_name)

        # select annotation in parte_span e controparte_span
        parte_idx = []
        controparte_idx = []
        for ann_id, ann in enumerate(annset):
            if ann.start >= cut_parte[0] and ann.end <= cut_parte[1]:
                parte_idx.append(ann.id)
            elif ann.start >= cut_controparte[0] and ann.end <= cut_controparte[1]:
                controparte_idx.append(ann.id)
            else:
                pass
        
        # classify annotations selected above and their cluster mates
        clusters = doc.features['clusters'][annset_name]
        for cluster in clusters:
            mention_ids = [men['id'] for men in cluster['mentions']]
            if set(mention_ids) & set(parte_idx):
                cluster['type'] = 'parte'
                for mention in cluster['mentions']:
                    ann = annset[mention['id']]
                    if 'types' in ann.features:
                        ann.features['types'] = ['parte'] + ann.features['types']
                    else:
                        ann.features['types'] = ['parte']
            if set(mention_ids) & set(controparte_idx):
                cluster['type'] = 'controparte'
                for mention in cluster['mentions']:
                    ann = annset[mention['id']]
                    if 'types' in ann.features:
                        ann.features['types'] = ['controparte'] + ann.features['types']
                    else:
                        ann.features['types'] = ['controparte']
            else:
                pass  
        
        if not 'pipeline' in doc.features:
            doc.features['pipeline'] = []
        doc.features['pipeline'].append('interessati')
            
        return doc