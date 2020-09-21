import csv
import common_vocabulary_node
import common_vocabulary_translator
import ftplib
import ntpath
import os
import shutil
import traceback

# These values represent a bit map of flags which can be combined e.g. type & subject.
TERM_KIND_TYPE = 1              # 0001
TERM_KIND_SUBJECT = 2           # 0010
TERM_KIND_PLACE = 4             # 0100
TERM_KIND_TYPE_AND_SUBJECT = 3  # 0011


class CommonVocabularyGenerator:
    def __init__(self, args):

        self.accepted_nodes = {}
        self.accepted_common_vocabulary_terms = list()
        self.accepted_row_count = 0
        self.csv_additions_file = args['additions_csv']
        self.csv_nomenclature_file = args['nomenclature_csv']
        self.csv_diff_file = args['diff_csv']
        self.csv_output_file = args['output_csv']
        self.csv_output_file_writer = None
        self.csv_previous_file = args['previous_csv']
        self.csv_translations_file = args['translations_csv']
        self.csv_vocabulary = args['vocabulary_csv']
        self.ftp_host = args['ftp_host']
        self.ftp_password = args['ftp_password']
        self.ftp_user = args['ftp_user']
        self.rejected_row_identifiers = list()
        self.vocabulary_additions = {}
        self.warnings = list()

        if not os.path.exists(self.csv_previous_file):
            shutil.copy(self.csv_vocabulary, self.csv_previous_file)

    def create_common_vocabulary_terms(self):
        self.read_non_nomenclature_terms_csv()

        try:
            # Attempt to delete the output file. If it's in use (e.g. open in Excel) and can't be
            # deleted, we can report the error immediately without processing the Nomenclature file.
            if os.path.exists(self.csv_output_file):
                os.remove(self.csv_output_file)

            # Process the Nomenclature terms.
            with open(self.csv_nomenclature_file, encoding="utf-8-sig") as csv_nomenclature_file:
                csv_reader = csv.DictReader(csv_nomenclature_file)
                print(f'\nTranslating {os.path.basename(self.csv_nomenclature_file)} ', end='')
                if not self.read_nomenclature_terms_csv(csv_reader):
                    self.report_statistics()
                    return False
                print("")

            # Create the output files.
            with open(self.csv_output_file, 'w', newline='', encoding='utf-8-sig') as csv_output_file:
                csv_writer = csv.writer(csv_output_file)
                self.write_output_file(csv_writer)

            return True

        except PermissionError:
            print(f'\n>>> Unable to delete {self.csv_nomenclature_file}')

        except:
            print(traceback.format_exc())

    def create_diff_file(self):
        action = ''
        identifier = 0
        new_term = ''
        new_terms = {}
        old_term = ''
        old_terms = {}

        def emit_diff(kind):
            print(f'{identifier}: [{old_term}] >>> [{new_term}]')
            csv_writer.writerow([action, kind, identifier, old_term, new_term])

        # Read the old CSV file into a list of dictionaries or old terms.
        with open(self.csv_previous_file, encoding="utf-8-sig") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                kind = row['Kind']
                identifier = int(row['Identifier'])
                row_id = f'{kind}-{identifier}'
                old_terms[row_id] = {'kind': kind, 'term': row['Term']}

        # Read the new CSV file into a list of dictionaries or new terms.
        with open(self.csv_output_file, encoding="utf-8-sig") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                kind = row['Kind']
                identifier = int(row['Identifier'])
                row_id = f'{kind}-{identifier}'
                new_terms[row_id] = {'kind': kind, 'term': row['Term']}

        # Create the diff file.
        with open(self.csv_diff_file, 'w', newline='', encoding='utf-8-sig') as csv_output_file:
            csv_writer = csv.writer(csv_output_file)
            csv_writer.writerow(['action', 'kind', 'identifier', 'old-term', 'new-term'])
            print("\n--- DIFF ------------------------------------------")

            # Emit differences for all terms that have been changed, added, or deleted.
            for row_id, old_data in old_terms.items():
                identifier = row_id[2:]
                old_kind = int(old_data['kind']);
                old_term = old_data['term']

                if row_id in new_terms:
                    # Found the identifier in the list of new terms.
                    new_term = new_terms[row_id]['term']
                    if old_term != new_term:
                        # The term's text changed.
                        action = 'UPDATE'
                        emit_diff(old_kind)
                else:
                    # The identifier is not in the list of new terms. It must have been deleted.
                    action = 'DELETE'
                    new_term = ''
                    emit_diff(old_kind)

            # Find all terms that have been added. They are ones in the new term list that are not in the old term list.
            for row_id, new_data in new_terms.items():
                if row_id not in old_terms:
                    identifier = row_id[2:]
                    new_term = new_data['term']
                    action = 'ADD'
                    old_term = ''
                    emit_diff(int(new_data['kind']))

        # The diff file has been written and closed. Upload it and the updated vocabulary to the server.
        self.upload_file_to_server(self.csv_diff_file)
        self.upload_file_to_server(self.csv_vocabulary)

    def create_node_for_non_nomenclature_term(self, identifier, kind, term):
        node = common_vocabulary_node.CommonVocabularyNode()
        node.identifier = str(identifier)
        node.common_vocabulary_term = term
        node.leaf_term = term.split(',')[-1].strip()
        node.term_kind = kind
        self.accepted_nodes[identifier] = node
        self.accepted_row_count += 1

    def create_nodes_for_non_nomenclature_terms(self):
        # Add additional terms that are not in Nomenclature. Use an identifier number that is
        # far higher than the largest Nomenclature identifier.

        for identifier, values in self.vocabulary_additions.items():
            kind = int(values[0])
            term = values[1]
            self.create_node_for_non_nomenclature_term(identifier, kind, term)

    @staticmethod
    def is_huge_object(term):
        # Huge objects are things like buildings, bridges, and boats that have their own top-level
        # term e.g. 'Structures', but when used as a Type are placed beneath `Object`. For example,
        # as a Subject, a bridge is a structure, but as a Type it's an object.
        return term.startswith('Structures') or term.startswith('Transportation') or term.startswith('Vessels')

    @staticmethod
    def normalize_term(term):
        normalized_term = ''
        parts = term.split(',')
        for part in parts:
            part = part.strip()
            if len(normalized_term):
                normalized_term += ', '
            normalized_term += part
        return normalized_term

    def read_nomenclature_terms_csv(self, csv_reader):
        translator = common_vocabulary_translator.CommonVocabularyTranslator(self.csv_translations_file)

        for row in csv_reader:
            if self.accepted_row_count % 1500 == 0:
                # Show progress.
                print('.', end='')

            # Read the row into a node object.
            node: common_vocabulary_node.CommonVocabularyNode
            node = common_vocabulary_node.CommonVocabularyNode(row)

            if node.reject:
                # Ignore rows that are level 1 or 2, or that are blank.
                continue

            self.accepted_row_count += 1
            try:
                node = translator.translate_nomenclature_to_common_vocabulary(node)
            except Exception as error:
                self.warning(node.identifier, error)
                return False

            # Set the node's kind.
            if node.common_vocabulary_term.startswith('Object'):
                node.term_kind = TERM_KIND_TYPE_AND_SUBJECT
            elif self.is_huge_object(node.common_vocabulary_term):
                node.term_kind = TERM_KIND_TYPE_AND_SUBJECT
            else:
                node.term_kind = TERM_KIND_TYPE

            if node.common_vocabulary_term in self.accepted_common_vocabulary_terms:
                self.warning(node.identifier, 'DUPLICATE ' + node.common_vocabulary_term)
            elif not node.common_vocabulary_term:
                self.warning(node.identifier, 'NOT TRANSLATED ' + node.nomenclature_tail)
            else:
                self.accepted_common_vocabulary_terms.append(node.common_vocabulary_term)

            self.accepted_nodes[node.identifier] = node

        return True

    def read_non_nomenclature_terms_csv(self):
        with open(self.csv_additions_file, 'r', encoding="utf-8-sig") as csv_additions_file:
            csv_reader = csv.DictReader(csv_additions_file)
            additions = list()
            for row in csv_reader:
                identifier = row['Identifier']
                if not identifier or identifier.startswith('#'):
                    # Skip blank rows.
                    continue
                if int(identifier) < 20000 or int(identifier) > 29999:
                    print(f'\n>>> OUT OF RANGE identifier {identifier} found in {self.csv_additions_file}')
                    exit()
                if identifier in additions:
                    print(f'\n>>> DUPLICATE identifier {identifier} found in {self.csv_additions_file}')
                    exit()
                self.vocabulary_additions[identifier] = (row['Kind'], self.normalize_term(row['Term']))
                additions.append(identifier)

    def report_statistics(self):
        # Print the total along with any errors or warnings.
        dictionary_len = len(self.accepted_nodes)
        print(f'\nTOTAL: {dictionary_len}')
        if dictionary_len + len(self.rejected_row_identifiers) != self.accepted_row_count:
            print(f'>>>> Total is not {self.accepted_row_count} as expected')
        for warning in self.warnings:
            print(f'>>> {warning}')

    def reject_row(self, identifier):
        self.rejected_row_identifiers.append(identifier)

    def upload_file_to_server(self, file_name):
        print(f'\nUpload: {file_name}')
        with ftplib.FTP(self.ftp_host) as ftp:
            try:
                ftp.login(self.ftp_user, self.ftp_password)
                with open(file_name, 'rb') as fp:
                    response = ftp.storlines("STOR " + ntpath.basename(file_name), fp)
                    if '226' in response:
                        print('FTP upload succeeded')
                    else:
                        print('>>> FTP upload failed')
            except ftplib.all_errors as e:
                print('>>> FTP error:', e)

    def validate_terms(self):
        nodes = {}
        for node in self.accepted_nodes.values():
            leaf = node.common_vocabulary_term.split(',')[-1].strip()
            if leaf in nodes:
                existing_node = nodes[leaf]
                if node.term_kind == existing_node.term_kind:
                    # Two nodes of the same kind have the same leaf term.
                    self.warning(node.identifier,
                                 f'DUPLICATE LEAF TERM: "{node.common_vocabulary_term}"'
                                 f' :: "{existing_node.identifier}: {existing_node.common_vocabulary_term}"')
            else:
                nodes[leaf] = node

    def warning(self, identifier, message):
        self.warnings.append(f'{identifier.rjust(5)}: {message}')

    def write_output_file(self, csv_output_file_writer):
        self.create_nodes_for_non_nomenclature_terms()
        self.validate_terms();

        # Sort the nodes alphabetically by their common vocabulary term.
        sorted_nodes = sorted(self.accepted_nodes.values(), key=lambda n: n.common_vocabulary_term)

        # Create the header row for the output CSV file.
        csv_output_file_writer.writerow(['Kind', 'Identifier', 'Term'])

        node: common_vocabulary_node.CommonVocabularyNode
        for node in sorted_nodes:
            if node.term_kind == TERM_KIND_TYPE_AND_SUBJECT:
                term = node.common_vocabulary_term
                if self.is_huge_object(term):
                    term = 'Object, ' + term
                self.write_term_to_output(csv_output_file_writer, node, term, TERM_KIND_TYPE)
                self.write_term_to_output(csv_output_file_writer, node, node.common_vocabulary_term, TERM_KIND_SUBJECT)
            else:
                self.write_term_to_output(csv_output_file_writer, node, node.common_vocabulary_term, node.term_kind)

        self.report_statistics()

    @staticmethod
    def write_term_to_output(csv_output_file_writer, node, term, term_kind):
        row = [term_kind, node.identifier, term]
        csv_output_file_writer.writerow(row)
        print(f'{node.identifier.rjust(5)}: {term_kind} {term}')
