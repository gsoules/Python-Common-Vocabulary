import csv
import common_vocabulary_node


class CommonVocabularyTranslator:
    def __init__(self, csv_translations_file):
        self.translation_rules = list()
        self.read_translation_rules(csv_translations_file)

    def read_translation_rule(self, csv_reader):
        for row in csv_reader:
            translation_rule = TranslationRule(
                row['Category'],
                row['Class'],
                row['Sub_Class'],
                row['Primary'],
                row['Secondary'],
                row['Identifier'],
                row['Translation'],
                row['Replace']
            )
            if not translation_rule.category or not translation_rule.translation:
                # Skip empty rows.
                continue
            self.translation_rules.append(translation_rule)

    def read_translation_rules(self, csv_translations_file):
        with open(csv_translations_file, encoding="utf-8-sig") as csv_translations_file:
            csv_reader = csv.DictReader(csv_translations_file)
            self.read_translation_rule(csv_reader)

    @staticmethod
    def derive_common_vocabulary_term_from_translated_term(node):
        # Remove any duplicate levels from the term hierarchy.
        # Example: Change 'Document|Memorabilia|Memorabilia' to 'Document|Memorabilia'
        # Duplicates occur on level 3 terms which have no primary term and so the sub-class or class gets included in
        # nomenclature_term. A duplicate gets introduced when a rule appends a sub-class or class name to the translated
        # term. Duplicates also occur if a rule uses its Replace column to rewrite part of the hierarchy incorrectly.
        node.common_vocabulary_term = ''
        parts = node.translated_term.split('|')
        for index, part in enumerate(parts):
            if index == 0:
                node.common_vocabulary_term = part
            else:
                if part == parts[index - 1]:
                    # Duplicate found.
                    if node.level == 3:
                        # Omit this part from the hierarchy.
                        continue

                    # Duplicate parts should only occur on level 3 nodes. Set the common vocabulary term to blank to
                    # indicate no translation occurred. Use the nomenclature term as a way of reporting the error.
                    node.common_vocabulary_term = ''
                    node.nomenclature_tail = f'Rule introduced redundant parts: {node.translated_term}'
                    break
                else:
                    # Not a duplicate. Keep this part.
                    node.common_vocabulary_term += f'|{part}'

        # Change the term separator from '|' to ','.
        # Because some Nomenclature terms use commas to separate lists e.g. "Leather, Horn & Shellworking",
        # first change ',' to '&' and then change '|' to ','.
        node.common_vocabulary_term = node.common_vocabulary_term.replace(',', ' &').replace('|', ', ')

    def translate_node(self, node, rule):
        node: common_vocabulary_node.CommonVocabularyNode
        rule: TranslationRule

        if rule.category != node.category:
            return False
        if rule.class_name and not rule.class_name == node.class_name:
            return False
        if rule.sub_class_name and not rule.sub_class_name == node.sub_class_name:
            return False
        if rule.primary and not rule.primary == node.primary_term:
            return False
        if rule.secondary and not rule.secondary == node.secondary_term:
            return False
        if rule.identifier and not rule.identifier == node.identifier:
            return False

        translation = rule.translation
        if '{class}' in translation:
            translation = translation.replace('{class}', node.class_name)
        elif '{sub_class}' in translation:
            translation = translation.replace('{sub_class}', node.sub_class_name)

        # Append the tail to the rule's translation text.
        if translation.endswith('{tail}'):
            node.translated_term = translation.replace('{tail}', node.nomenclature_tail)
        elif translation.endswith('{leaf}'):
            node.translated_term = translation.replace('{leaf}', node.leaf_term)
        else:
            node.translated_term = translation

        if rule.replace:
            # The replace rule consists of pairs of old/new values. Loop over each pair and make the replacement.
            parts = rule.replace.split(',')
            if len(parts) % 2 != 0:
                raise Exception(f'INVALID SYNTAX in Replace rule: {rule.replace}')
            for index, part in enumerate(parts):
                if index % 2:
                    # Skip the second part of the pair.
                    continue
                old = parts[index].strip().replace('"', '')
                translation = parts[index + 1].strip().replace('"', '')
                node.translated_term = node.translated_term.replace(old, translation)

        self.derive_common_vocabulary_term_from_translated_term(node)

        return True

    def translate_nomenclature_to_common_vocabulary(self, node):
        for rule in self.translation_rules:
            if self.translate_node(node, rule):
                return node

        # Should never get here.
        return node


class TranslationRule:
    def __init__(self,
                 category,
                 class_name='',
                 sub_class_name='',
                 primary='',
                 secondary='',
                 identifier='',
                 translation='',
                 replace=''
                 ):
        self.category = category
        self.class_name = class_name
        self.sub_class_name = sub_class_name
        self.primary = primary
        self.secondary = secondary
        self.identifier = identifier
        self.translation = translation
        self.replace = replace


