import argparse
from fastapi import FastAPI, Body
import uvicorn
import re
from gatenlp import Document
import pandas as pd

def identify_sections(doc):
  '''
  identify different sections in the text as per art.132 Codice di procedura 
  civile
  '''
  offset = 0
  current_section = ''
  section_offset = {}
  end_preambolo = False
  end_conclusioni = False
  end_fatto_e_diritto = False
  end_dispositivo = False
  end_firma_e_data = False
  i = 0
  
  for line in doc.splitlines(keepends=True):
    if not end_preambolo:
      end_preambolo = True
      current_section = 'preambolo'
    elif re.search('^CONCLUSIONI', line) and not end_conclusioni:
      end_conclusioni = True
      current_section = 'conclusioni'
    elif re.search('^FATTO (E DIRITTO)?$|^SENTENZA$', line.strip()) and not end_fatto_e_diritto:     
      end_fatto_e_diritto = True
      current_section = 'fatto_e_diritto'      
    elif re.search('P( )?(.)?( )?Q( )?(.)?( )?M|^MOTIV(AZION)?[EI]|PTM', line, flags=re.IGNORECASE) and not end_dispositivo:
      end_dispositivo = True
      current_section = 'dispositivo' 
    else:
      try:
        if (any (tribunale for tribunale in distribuzione_territoriale_uffici['Tribunale'].str.lower()\
                if tribunale in line.lower())\
                or re.search('remoto', line, flags=re.IGNORECASE))\
                and re.search('[ \.-/](\d){2}(\d){2}?', line, flags=re.IGNORECASE)\
                and re.search('presidente|giudice|GOT', doc.splitlines()[i+1], flags=re.IGNORECASE)\
                and not end_firma_e_data: #sede di tribunale + anno a quattro cifre
          end_firma_e_data = True
          current_section = 'firma_e_data'
      except:
        continue
    
    i+=1
    final_offset = offset + len(line)
    section_offset.setdefault(current_section, [offset, offset])[1] = final_offset
    offset = final_offset

  return section_offset

def add_sections_to_gatenlp(gnlp_doc):
  '''
  Add sections to a gateNLP document
  '''
  annset = gnlp_doc.annset("Sections")
  offset_dict = identify_sections(gnlp_doc.text)

  # fix offsets supposing start is more accurate then end
  prev_start = len(gnlp_doc.text) - 1
  for key, value in reversed(sorted(offset_dict.items(), key=lambda x: x[1][0])):
    # if value[1] != prev_start:
    #   print('correcting', value, (value[0], prev_start))
    value[1] = prev_start
    prev_start = value[0]

  for key, value in offset_dict.items():
    _start = value[0]
    _end = value[1]

    # print('corrected', value)

    annset.add(_start, _end, key, {"mention":""})
  return gnlp_doc

app = FastAPI()

@app.post('/api/sectionator')
async def sectionator(doc: dict = Body(...)):
    doc = Document.from_dict(doc)

    add_sections_to_gatenlp(doc)

    return doc.to_dict()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="host to listen at",
    )
    parser.add_argument(
        "--port", type=int, default="30311", help="port to listen at",
    )
    parser.add_argument(
        "--distribuzione_territoriale_uffici", dest='distribuzione_territoriale_uffici', type=str, default="distribuzione_territoriale_uffici.csv", help="Path to distribuzione_territoriale_uffici.csv",
    )

    # pool to run tint in parallel # TODO
    #pool = Pool(1)

    args = parser.parse_args()

    distribuzione_territoriale_uffici = pd.read_csv(args.distribuzione_territoriale_uffici, index_col='N°')

    uvicorn.run(app, host = args.host, port = args.port)