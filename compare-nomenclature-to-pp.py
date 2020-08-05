import csv
import os

csv_file_path = os.getcwd() + '\\data\\'
common_vocabulary_csv = f'{csv_file_path}output-nomenclature-sortEn_2020-05-18.csv'

pp_csv = f'{csv_file_path}pp-lexicon3-tremont.csv'
pp_csv_natural_history = f'{csv_file_path}pp-lexicon-natural-history-extension.csv'

natural_leaf_terms = list()
pp_terms = list()
pp_natural_history = list()

with open(common_vocabulary_csv, encoding="utf-8-sig") as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        identifier = int(row['Identifier'])
        kind = int(row['Kind'])
        if kind == 2 or kind == 4:
            continue
        leaf_term = row['Leaf Term']
        full_term = row['Common Term']
        if leaf_term in natural_leaf_terms:
            print(f'>>> DUPLICATE LEAF TERM: {identifier}: {kind} :: {leaf_term} :: {full_term}')
        else:
            natural_leaf_terms.append(leaf_term)

with open(pp_csv, encoding="utf-8-sig") as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        inverted_term = row['TERM']
        parts = inverted_term.split(',')
        normal_term = ''
        if len(parts) > 1:
            normal_term = parts[1].strip() + ' ' + parts[0].strip()
        else:
            normal_term = inverted_term
        pp_terms.append(normal_term)

with open(pp_csv_natural_history, encoding="utf-8-sig") as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        pp_natural_history.append(row['TERM'])

natural_leaf_terms.sort()
pp_terms.sort()

index = 1
print('PP terms not found in Nomenclature')
print('==================================')
for pp_term in pp_terms:
    if pp_term not in natural_leaf_terms and pp_term not in pp_natural_history:
        print(f'{index}: {pp_term}')
        index += 1

index = 1
print('\nNomenclature terms not found in PP')
print('==================================')
for nomenclature_term in natural_leaf_terms:
    if nomenclature_term not in pp_terms:
        print(f'{index}: {nomenclature_term}')
        index += 1

