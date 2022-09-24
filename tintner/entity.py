from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Generator, Callable, Set
# import progiustizia.annotazione.PreprocessUtilities as pu
import io
import json
import os
import sys
import hashlib
import colorsys


class InvalidEntityMention(Exception):
    pass


class EntityMention:
    # pandas tsv column names and types
    df_columns = [
        'doc_id', 'begin', 'end',
        'text', 'score', 'type'
    ]
    df_types = {
        'doc_id': 'str',
        'begin': 'int',
        'end': 'int',
        'text': 'str',
        'score': 'float',
        'type': 'str'
    }

    def is_valid(self) -> bool:
        return self.end > self.begin and isinstance(self.begin, int) and isinstance(self.end, int)

    def __init__(
            self,
            doc_id: str,
            begin: int,
            end: int,
            text: str,
            type_: str,
            score: float = 0,
            link=None,
            attrs={}):
        self.doc_id = str(doc_id)
        self.begin = int(begin)
        self.end = int(end)
        self.text = str(text)
        self.score = float(score)
        self.type_ = str(type_)
        self.link = link
        self.attrs = attrs

        if not self.is_valid():
            raise InvalidEntityMention(self.__repr__())

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        repr_link = f' <{self.link}>' if self.link is not None else ''
        return f'<EntityMention {self.doc_id}[{self.begin}:{self.end}] "{self.text}" {self.score} {self.type_}{repr_link}>'

    def __len__(self):
        return self.end - self.begin

    def __hash__(self):
        # EntityMention is unique for a document and a position
        return hash((self.doc_id, self.begin, self.end))

    def __lt__(self, other):
        # begin less than other
        return self.begin < other.begin

    # TODO test match functions

    def strong_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        # begin and end matches
        ret = (e1.doc_id == e2.doc_id
               and e1.begin == e2.begin
               and e1.end == e2.end)
        return ret

    def strong_typed_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        # begin end and type matches
        ret = (EntityMention.strong_mention_match(e1, e2)
               and e1.type_ == e2.type_)
        return ret

    def left_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        ret = (e1.doc_id == e2.doc_id
               and e1.begin == e2.begin)
        return ret

    def left_typed_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        ret = (EntityMention.left_mention_match(e1, e2)
               and e1.type_ == e2.type_)
        return ret

    def right_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        ret = (e1.doc_id == e2.doc_id
               and e1.end == e2.end)
        return ret

    def right_typed_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        ret = (EntityMention.rigth_mention_match(e1, e2)
               and e1.type_ == e2.type_)
        return ret

    def approximate_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        # one mention is contained in the other
        # 'filename == "{filename}" & ((start <= {start} & end >= {end}) | (start >= {start} & end <= {end}))'),
        ret = (e1.doc_id == e2.doc_id
               and ((e1.begin <= e2.begin and e2.end <= e1.end)
                    or (e2.begin <= e1.begin and e1.end <= e2.end)))

        return ret

    def approximate_typed_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        ret = (EntityMention.approximate_mention_match(e1, e2)
               and e1.type_ == e2.type_)
        return ret

    def partial_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        # the two mentions have intersection
        # 'filename == "{filename}" & ((start <= {start} & end >= {start}) | (start >= {start} & start <= {end}))'),
        ret = (e1.doc_id == e2.doc_id
               and (e1.begin <= e2.begin and e2.begin <= e1.end)
               or (e2.begin <= e1.begin and e1.begin <= e2.end))
        return ret

    def partial_typed_mention_match(e1: EntityMention, e2: EntityMention) -> bool:
        ret = (EntityMention.partial_mention_match(e1, e2)
               and e1.type_ == e2.type_)
        return ret

    def __eq__(self, other: EntityMention,
               matchFunction: Callable[[EntityMention, EntityMention], bool] = None) -> bool:
        if matchFunction is None:
            matchFunction = EntityMention.strong_typed_mention_match
        return EntityMention.__eq__(self, other, matchFunction)

    def __eq__(e1: EntityMention, e2: EntityMention,
               matchFunction: Callable[[EntityMention, EntityMention], bool] = None) -> bool:
        if matchFunction is None:
            matchFunction = EntityMention.strong_typed_mention_match
        return matchFunction(e1, e2)

    def to_dict(self):
        ret = {
            'doc_id': self.doc_id,
            'begin': self.begin,
            'end': self.end,
            'text': self.text,
            'score': self.score,
            'type': self.type_,
            # 'link': self.link # TODO for linking
        }
        return ret

    def copy(self):
        return EntityMention(
            doc_id=self.doc_id,
            begin=self.begin,
            end=self.end,
            text=self.text,
            score=self.score,
            type_=self.type_,
            link=self.link
        )

    def from_dict(dict_ent: dict) -> EntityMention:
        ret = EntityMention(
            doc_id=dict_ent['doc_id'],
            begin=dict_ent['begin'],
            end=dict_ent['end'],
            text=dict_ent['text'],
            score=dict_ent['score'],
            type_=dict_ent['type'],
            link=dict_ent.get('link', None)
        )
        return ret

    def from_custom_json_annotation(dict_ent: dict, doc_id, text) -> EntityMention:
        ret = EntityMention(
            doc_id=doc_id,
            begin=dict_ent['start'],
            end=dict_ent['end'],
            text=text[dict_ent['start']:dict_ent['end']],
            score=0,
            type_=dict_ent['type'],
            link=dict_ent.get('link', None)
        )
        return ret

    def from_spacy(spacy_ents, doc_id: str, ignore_errors: bool = False) -> Generator[EntityMention]:
        for entity in spacy_ents:
            begin = entity.start_char
            end = entity.end_char
            text = entity.text
            type_ = entity.label_
            score = 0

            try:
                ent = EntityMention(
                    doc_id=doc_id,
                    begin=begin,
                    end=end,
                    text=text,
                    type_=type_,
                    score=score
                )

                yield ent
            except InvalidEntityMention as e:
                if not ignore_errors:
                    raise e

    def from_tint(tint_out: dict, doc_id: str, ignore_errors: bool = False) -> Generator[EntityMention]:
        for sentence in tint_out['sentences']:
            for token in sentence['tokens']:
                # produce O tokens too. they'll be removed after grouping
                begin = token['characterOffsetBegin']
                end = token['characterOffsetEnd']
                text = token['word']
                score = 0
                type_ = token['ner']

                try:
                    ent = EntityMention(
                        doc_id=doc_id,
                        begin=begin,
                        end=end,
                        text=text,
                        type_=type_,
                        score=score
                    )

                    if type_ == 'DATE':
                        ent.attrs['normalized_date'] = token['normalizedNER']

                    yield ent

                except InvalidEntityMention as e:
                    if not ignore_errors:
                        raise e

    def from_expert_ai(expert_ai_out: dict, doc_id: str, ignore_errors: bool = False):
        for ent in expert_ai_out:
            # produce O tokens too. they'll be removed after grouping
            begin = ent.positions[0].start
            end = ent.positions[0].end
            text = ent.lemma
            score = 0
            type_ = ent.type_

            try:
                ent = EntityMention(
                    doc_id=doc_id,
                    begin=begin,
                    end=end,
                    text=text,
                    type_=type_,
                    score=score
                )

                yield ent

            except InvalidEntityMention as e:
                if not ignore_errors:
                    raise e

    def group_from_tint(tint_out: dict, doc_id: str, ignoreOutside=True, ignore_errors: bool = False, doc: str = None) -> List[
        EntityMention]:
        ent_generator = EntityMention.from_tint(tint_out, doc_id, ignore_errors)
        # if ignoreOutside:
        #     ent_generator = filter(lambda e: e.type_ != 'O', ent_generator)
        tintEnts = list(ent_generator)
        grouped = EntityMention.group_entities(tintEnts, doc)
        if ignoreOutside:
            grouped = [e for e in grouped if e.type_ != 'O']
        return grouped

    def fromBertEntity(bertentity, doc_id: str) -> EntityMention:
        ent = EntityMention(
            doc_id=doc_id,
            begin=bertentity['start'],
            end=bertentity['end'],
            text=bertentity['word'],
            score=0,  # TODO propagate and get Bert score
            type_=bertentity['entity_group']
        )

        return ent

    def from_transformer_syntok(trf_syntok_entities, doc_id: str, ignore_errors: bool = False) -> List[EntityMention]:
        for sent in trf_syntok_entities:
            for ent in sent:
                try:
                    ret = EntityMention.fromBertEntity(ent, doc_id)
                    yield ret
                except InvalidEntityMention as e:
                    if not ignore_errors:
                        raise e

    def from_electra_sliding_window(entities, doc_id: str, ignore_errors: bool = False) -> List[EntityMention]:
        for ent in entities:
            try:
                ret = EntityMention.fromBertEntity(ent, doc_id)
                yield ret
            except InvalidEntityMention as e:
                if not ignore_errors:
                    raise e

    def from_inception_json(path, doc_id=None, ignore_errors=False, text_path=None):
        with open(path, 'r', encoding='utf-8') as fd:
            inception = json.load(fd)

        doc_text = None
        if text_path is not None:
            with open(text_path, 'r', encoding='utf-8') as fd:
                doc_text = fd.read()

        if doc_id is None:
            doc_id = ".".join(os.path.basename(path).split(".")[:-1])
        inception_entities = inception["_views"]["_InitialView"]["NamedEntity"]

        for row in inception_entities:
            try:
                ent = EntityMention(
                    doc_id=doc_id,
                    # seems inception json files don't contain begin if they start with a mention
                    begin=row['begin'] if 'begin' in row else 0,
                    end=row['end'],
                    text="" if doc_text is None else doc_text[row['begin']:row['end']],
                    score=0,
                    type_=row['value']
                )

                yield ent
            except InvalidEntityMention as e:
                if not ignore_errors:
                    raise e

    def nearLeft(mapping, lefti):
        i = lefti
        while i >= mapping["min"]:
            if str(i) in mapping:
                return mapping[str(i)]
            i -= 1
        return 0
    def nearRight(mapping, righti):
        i = righti
        while i <= mapping["max"]:
            if str(i) in mapping:
                return mapping[str(i)]
            i += 1
        return -1

    def mapping_transform(mapping, entities, original_text=None, original_path=None):
        if original_text is None and original_path is None:
            # we need info about original file length
            # maybe include this info into the mapping # TODO
            raise Exception('either original_text or original_path must be passed to mapping transform.')
        if original_path is not None and original_text is None:
            with open(original_path, 'r', encoding='utf-8') as fd:
                original_text = fd.read()
        for ent in entities:
            new_ent = ent.copy()
            new_ent.begin = EntityMention.nearLeft(mapping, ent.begin)
            nearRight_ = EntityMention.nearRight(mapping, ent.end)
            new_ent.end = nearRight_ if nearRight_ >= 0 else len(original_text)
            if original_text is not None:
                new_ent.text = original_text[new_ent.begin:new_ent.end]
            yield new_ent

    def from_tsv(path, python_style_end=True, ignore_errors=False):
        """
        python_style_end=True means:
            Given text='Hello world',
            text[0:5] == 'Hello' that is the end character, the char at 5 in this case, is excluded.
        otherwise given the same text,
            text[0:5] == 'Hello ' where the chat at 5 is included.
        """

        tsv = pd.read_csv(path, sep='\t', names=EntityMention.df_columns, dtype=EntityMention.df_types)
        tsv.sort_values(by=['doc_id', 'begin'], inplace=True)

        for _, row in tsv.iterrows():
            try:
                ent = EntityMention(
                    doc_id=row['doc_id'],
                    begin=row['begin'],
                    end=row['end'] if python_style_end else row['end'] + 1,
                    text=row['text'],
                    score=row['score'],
                    type_=row['type']
                )

                yield ent
            except InvalidEntityMention as e:
                if not ignore_errors:
                    raise e

    # doesn't work well. as it is used only for visualization now it's worth to implement our own html rendering
    def to_spacy(entities, text):
        # todo fix
        import spacy
        from spacy.tokens.span import Span

        def getAdjacentTokens(indexes, idx):
            for i,val in enumerate(indexes):
                if val > idx:
                    return i-1
            return i
        def getSpacySpanFromIdx(indexes, begin, end):
            begin_token = getAdjacentTokens(indexes, begin)
            end_token = getAdjacentTokens(indexes, end-1)
            return begin_token, end_token


        nlp = spacy.load('it_core_news_lg', disable=['tok2vec', 'morphologizer', 'tagger', 'parser', 'ner', 'attribute_ruler', 'lemmatizer'])

        doc = nlp(text, disable=['tok2vec', 'morphologizer', 'tagger', 'parser', 'ner', 'attribute_ruler', 'lemmatizer'])
        indexes = [t.idx for t in doc]
        for ent in entities:
            ss, se = getSpacySpanFromIdx(indexes, ent.begin, ent.end)
            span = Span(doc, start=ss, end=se+1, label=ent.type_)
            try:
                doc.ents += (span,)
            except ValueError:
                print('ValueError when creating spacy entity.', file=sys.stderr)
                pass

        return doc

    # def type_colors(type_):
    #     type_colors = {
    #         'ORG': '#7aecec',
    #         'DATE': '#bfe1d9',
    #         'PER': '#ddd',
    #         'MONEY': '#e4e7d2',
    #         'LOC': '#ff9561',
    #     }
    #     color = type_colors.get(type_)
    #     if color is None:
    #         color = '#eee'
    #     return color

    def type_colors(type_):
        hue = abs(hash(type_)) % 360 / 360
        r, g, b = colorsys.hsv_to_rgb(hue, 0.15, 1)
        r *= 255
        g *= 255
        b *= 255

        return 'rgb({}, {}, {})'.format(r, g, b)

    def render(mentions: list, text: str, title: str = "Render", type_colors = None) -> str:
        """Returns an html version of the TEXT enritched with MENTIONS
        (eventually adding something at the very BEGIN and at the END)"""
        if type_colors is None:
            type_colors = EntityMention.type_colors

        begin = '''<!DOCTYPE html>
<html lang="it">
    <head>
        <title>{}</title>
    </head>

    <body style="font-size: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol'; padding: 4rem 2rem; direction: ltr">
<figure style="margin-bottom: 6rem">
<div class="entities" style="line-height: 2.5; direction: ltr">'''.format(title)
        end = '''</div>
</figure>
</body>
</html>'''
        out = begin
        i = 0
        for mention in sorted(mentions):
            #print((i, mention.begin, mention.end))
            htmlMention = '''<mark class="entity" style="background: {}; padding: 0.45em 0.6em; margin: 0 0.25em; line-height: 1; border-radius: 0.35em;">
    {}
    <span style="font-size: 0.8em; font-weight: bold; line-height: 1; border-radius: 0.35em; vertical-align: middle; margin-left: 0.5rem">{}</span>
</mark>'''.format(type_colors(mention.type_), text[mention.begin:(mention.end)].replace('\n', '</br>'), mention.type_)
            if mention.begin > 0:
                out += text[i:mention.begin].replace('\n', '</br>')
            out += htmlMention
            i = mention.end
        out += text[i:].replace('\n', '</br>')
        out += end
        return out

    def to_tsv(entities: List[EntityMention], path: str):
        def dict_generator(entities):
            for entity in entities:
                res = entity.to_dict()
                res['text'] = res['text'].replace('\n', ' ')
                yield res

        df = pd.DataFrame(dict_generator(entities), columns=EntityMention.df_columns)
        df.astype(EntityMention.df_types, copy=False)
        df.sort_values(by=['doc_id', 'begin'], inplace=True)

        df.to_csv(path, sep='\t', index=False, header=False)

    def by_doc(entities: List[EntityMention]) -> dict:
        ret = {}
        for e in entities:
            if e.doc_id not in ret:
                ret[e.doc_id] = []
            ret[e.doc_id].append(e)

        return ret

    def merge(
            entitiesSources: List[List[EntityMention]],
            matchFunction: Callable[[List[EntityMention]], bool] = None,
            multiEntitiesThreshold: float = 0.7
    ) -> Set[EntityMention]:
        """
        entitiesSources: List of entities sources. Currently only 2 sources are supported.
        multiEntitiesThreshold: mention divided in multiple entities is preferred to the bigger one
            only if its total length is at least bigger * acceptableThreshold.
        matchFunction: accepts a list of entities and return True if they match
            (currently only two entities in the list).

        N.B. only pass to this function entities from the same document
        """
        if len(entitiesSources) != 2:
            raise Exception('Currently only 2 entity Sources are supported')

        # ensure entities are sorted
        for i in range(len(entitiesSources)):
            entitiesSources[i] = sorted(entitiesSources[i])

        iterators = [iter(s) for s in entitiesSources]
        current = [next(i) for i in iterators]
        merged = set()

        def is_current_match_default(current):
            return current[0].__eq__(current[1], EntityMention.partial_mention_match)

        if matchFunction is None:
            matchFunction = is_current_match_default

        doc_id = current[0].doc_id

        while True:

            # check doc_id; this function has to be called one doc per time
            for e in current:
                if e.doc_id != doc_id:
                    msg = f"""ERROR: merge can only merge entities of the same document.
                    Received entities from both {doc_id} and {e.doc_id}"""
                    raise Exception(msg)

            to_merge = [set() for _ in current]
            while matchFunction(current):
                # merge
                # which to append?
                # the bigger? check if next mentions matches the bigger?
                min_end = np.argmin([e.end for e in current])

                # save current for merging later
                for i in range(len(current)):
                    # set takes care of duplicates
                    to_merge[i].add(current[i])

                # checking if next "smaller" entity mention matches the "bigger"
                try:
                    current[min_end] = next(iterators[min_end])
                except StopIteration:
                    break
            if min(len(s) for s in to_merge) > 0:
                # merge what's in to_merge
                # get the longest (here entities are already grouped so we pick the most specific(?))
                # or maybe consider the lengths: if they are similar get the most specific otherwise the longest
                numLengths = [len(s) for s in to_merge]
                longestByNum = np.argmax(numLengths)
                lengthSums = np.array([sum(len(e) for e in s) for s in to_merge])
                # normalize
                lengthSums = lengthSums / max(lengthSums)
                longestByLengthSums = np.argmax(lengthSums)

                if max(numLengths) == 1:
                    # single mention matched single mention
                    # TODO reason about types (?), source (?)
                    # append the longest for now
                    e = next(iter(to_merge[longestByLengthSums]))
                    if e in merged:
                        print('Trying to add', e, 'twice')
                        raise Exception('Trying to add', e, 'twice')
                    merged.add(e)
                    # print('Appending 1', e)
                else:
                    # multiple mentions matched single/multiple mentions
                    if lengthSums[longestByNum] >= multiEntitiesThreshold:
                        # get the longestByNum that is the most specific/divided
                        for e in to_merge[longestByNum]:
                            # print('Appending longestbynum', e)
                            if e in merged:
                                print('Trying to add', e, 'twice')
                                raise Exception('Trying to add', e, 'twice')
                            merged.add(e)
                    else:
                        # get the longestByLengthSums
                        for e in to_merge[longestByLengthSums]:
                            # print('Appending longestbysums', e)
                            if e in merged:
                                print('Trying to add', e, 'twice')
                                raise Exception('Trying to add', e, 'twice')
                            merged.add(e)

                # remove from current what is in to_merge
                try:
                    for i in range(len(current)):
                        for s in to_merge:
                            if current[i] in s:
                                # next
                                current[i] = next(iterators[i])
                except StopIteration:
                    break

            if not matchFunction(current):
                # current mentions does not match
                # go on with the iteration looking for matches
                # increment the minimum
                argmin = np.argmin([e.begin for e in current])
                try:
                    # append the current one
                    # print('Apppending non match', current[argmin])
                    if current[argmin] in merged:
                        print('Trying to add', current[argmin], 'twice')
                        raise Exception('Trying to add', current[argmin], 'twice')
                    merged.add(current[argmin])
                    current[argmin] = next(iterators[argmin])
                except StopIteration:
                    break
            else:
                # they match and they are managed by the while at next iteration
                pass

        # probably only one iterator is finished
        # finish the others
        for it in iterators:
            try:
                while True:
                    e = next(it)
                    # print('Appending at the end', e)
                    if e in merged:
                        print('Trying to add', e, 'twice')
                        raise Exception('Trying to add', e, 'twice')
                    merged.add(e)
            except StopIteration:
                continue

        return merged

    def group_sub_entities(entities: List[EntityMention], doc: str = None) -> EntityMention:
        """
        Group together the adjacent tokens with the same entity predicted.

        Args:
            entities (:obj:`EntityMention`): The entities predicted by the pipeline.

        Adapted from https://huggingface.co/transformers/main_classes/pipelines.html#transformers.TokenClassificationPipeline.group_sub_entities
        """
        # Get the first entity in the entity group
        type_ = entities[0].type_
        doc_id = entities[0].doc_id
        begin = entities[0].begin
        end = entities[-1].end
        scores = np.nanmean([entity.score for entity in entities])
        if doc:
            text = doc[begin:end]
        else:
            text = ' '.join([entity.text for entity in entities])

        attrs = {}
        for e in entities:
            # same key on right overwrites key on left: keeping the first
            attrs = {**e.attrs, **attrs}

        entity_group = EntityMention(
            doc_id=doc_id,
            begin=begin,
            end=end,
            score=scores,
            type_=type_,
            text=text,
            attrs=attrs
        )

        return entity_group

    def group_entities(entities: List[EntityMention], doc: str = None) -> List[EntityMention]:
        """
        Find and group together the adjacent tokens with the same entity predicted.

        Args:
            entities (:obj:`EntityMention`): The entities predicted by the pipeline.

        Adapted from https://huggingface.co/transformers/main_classes/pipelines.html#transformers.TokenClassificationPipeline.group_entities
        """

        entity_groups = []
        entity_group_disagg = []

        if entities:
            last_idx = len(entities) - 1

        for entity_idx, entity in enumerate(entities):

            is_last_idx = entity_idx == last_idx
            if not entity_group_disagg:
                entity_group_disagg += [entity]
                if is_last_idx:
                    entity_groups += [EntityMention.group_sub_entities(entity_group_disagg, doc)]
                continue

            # If the current entity is similar and adjacent to the previous entity, append it to the disaggregated entity group
            # The split is meant to account for the "B" and "I" suffixes
            # Shouldn't merge if both entities are B-type
            if (entity.type_.split("-")[-1] == entity_group_disagg[-1].type_.split("-")[-1]
                    and entity.type_.split("-")[0] != "B"):

                entity_group_disagg += [entity]
                # Group the entities at the last entity
                if is_last_idx:
                    entity_groups += [EntityMention.group_sub_entities(entity_group_disagg, doc)]
            # If the current entity is different from the previous entity, aggregate the disaggregated entity group
            else:
                entity_groups += [EntityMention.group_sub_entities(entity_group_disagg, doc)]
                entity_group_disagg = [entity]
                # If it's the last entity, add it to the entity groups
                if is_last_idx:
                    entity_groups += [EntityMention.group_sub_entities(entity_group_disagg, doc)]

        return entity_groups


def expert_ai(data_expertai, text):
    from expertai.nlapi.edge.client import ExpertAiClient
    client = ExpertAiClient()
    client.set_host('localhost', 6699)
    output = client.named_entity_recognition(text)
    output.entities.sort(key=lambda x: x.positions[0].start)
    # doc = pu.get_doc_id(data_expertai)
    res = io.StringIO()
    mentions = EntityMention.from_expert_ai(output.entities, data_expertai, True)
    res = EntityMention.to_tsv(mentions, res)
    return res
