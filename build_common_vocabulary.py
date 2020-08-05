import common_vocabulary_generator
import os

data_file_path = os.getcwd() + '\\data\\'

args = {
    'nomenclature_csv': f'{data_file_path}input-nomenclature-sortEn_2020-05-18.csv',
    'output_csv': f'{data_file_path}digital-archive-vocabulary.csv',
    'translations_csv': f'{data_file_path}input-translations.csv',
    'additions_csv': f'{data_file_path}input-additional-terms.csv',
    'previous_csv': f'{data_file_path}input-previous-digital-archive-vocabulary.csv',
    'diff_csv': f'{data_file_path}digital-archive-diff.csv',
    'vocabulary_csv': f'{data_file_path}digital-archive-vocabulary.csv',
    'ftp_host': 'ftp.digitalarchive.us',
    'ftp_user': 'vocabulary@digitalarchive.us',
    'ftp_password': '=}+s7g^BTc00'
}

generator = common_vocabulary_generator.CommonVocabularyGenerator(args)

if generator.create_common_vocabulary_terms():
    generator.create_diff_file()
