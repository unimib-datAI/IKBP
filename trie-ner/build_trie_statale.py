from TrieNER import TrieNER
import pandas as pd

tner = TrieNER()

# CARTE POSTALI (NomeCognome, Natoa, CF)
data = pd.read_csv('./data/cartepostali.csv', index_col=False)
# add persons
tner.add_entities(list(data['NomeCognome']), 'PER')
# add places
tner.add_entities(list(data['Natoa']), 'LOC', False)

# DOMANDE INTEGRATE (Cognome, Nome, Luogo, CF)
data = pd.read_csv('./data/domande_integrate.csv', index_col=False)
# add persons
tner.add_entities(list(data['Nome'] + ' ' + data['Cognome']), 'PER')
# add places
tner.add_entities(list(data['Luogo']), 'LOC', False)

# NUCLEI FAMILIARI (CognomeCongiunto, NomeCongiunto, Luogo, CFDichiarante)
data = pd.read_csv('./data/nucleifamiliari.csv', index_col=False)
# add persons
tner.add_entities(list(data['NomeCongiunto'] + ' ' + data['CognomeCongiunto']), 'PER')

tner.save()