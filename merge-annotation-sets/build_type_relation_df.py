import pandas as pd

def build_df():
  tuples = [('CONTROPARTE', 'PER'), ('CONTROPARTE', 'ORG'), ('GIUDICE', 'PER'), ('PARTE', 'PER'), ('PER', 'ORG'), ('TRIBUNALE', 'LOC')]
  df = pd.DataFrame(tuples, columns=['type', 'root_type'])
  df.to_csv('./type_relation_df.csv')

build_df()
