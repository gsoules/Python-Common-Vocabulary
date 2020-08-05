class CommonVocabularyNode:
    def __init__(self, row=None):
        self.category = ''
        self.class_name = ''
        self.common_vocabulary_term = ''
        self.identifier = ''
        self.leaf_term = ''
        self.level = 0
        self.nomenclature_tail = ''
        self.reject = False
        self.primary_term = ''
        self.secondary_term = ''
        self.sub_class_name = ''
        self.tertiary_term = ''
        self.term_kind = 0
        self.translated_term = ''

        if row:
            self.read_nomenclature_columns(row)

    def construct_nomenclature_tail(self):
        if self.level <= 2:
            # Skip rows that have no class or sub class name because they have no leaf term.
            self.reject = True
            return

        if self.primary_term:
            # Construct the tail from the primary, secondary, and tertiary terms.
            self.nomenclature_tail = self.primary_term
            self.leaf_term = self.primary_term
            if self.secondary_term:
                self.nomenclature_tail += '|' + self.secondary_term
                self.leaf_term = self.secondary_term
            if self.tertiary_term:
                self.nomenclature_tail += '|' + self.tertiary_term
                self.leaf_term = self.tertiary_term
        else:
            # There is no primary term so use the subclass or class name as both the tail and leaf term.
            if self.sub_class_name:
                self.nomenclature_tail = self.sub_class_name
            elif self.class_name:
                self.nomenclature_tail = self.class_name
            self.leaf_term = self.nomenclature_tail

    def read_nomenclature_columns(self, row):
        self.category = row['Natural_Order_EN_Category']

        if not self.category:
            # Skip the row if the category is blank.
            self.reject = True
            return

        self.identifier = row['Identifier']
        self.level = int(row['level'])

        self.class_name = row['Natural_Order_EN_Class']

        self.sub_class_name = row['Natural_Order_EN_Sub_Class']
        if '(blank sub-class)' in self.sub_class_name:
            self.sub_class_name = ''

        self.primary_term = row['Natural_Order_EN_Primary_Term']
        self.secondary_term = row['Natural_Order_EN_Secondary_Term']
        self.tertiary_term = row['Natural_Order_EN_Tertiary_Term']

        # Replace closing single quote with apostrophe.
        self.primary_term = self.primary_term.replace("’", "'")
        self.secondary_term = self.secondary_term.replace("’", "'")
        self.tertiary_term = self.tertiary_term.replace("’", "'")

        self.construct_nomenclature_tail()

