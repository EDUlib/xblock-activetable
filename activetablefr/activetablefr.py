# -*- coding: utf-8 -*-
"""An XBlock with a tabular problem type that requires students to fill in some cells."""
from __future__ import absolute_import, division, unicode_literals

import textwrap

from xblock.core import XBlock
from xblock.fields import Dict, Float, Integer, Scope, String
from xblock.fragment import Fragment
from xblock.validation import ValidationMessage
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from .cells import NumericCell
from .parsers import ParseError, parse_table, parse_number_list

loader = ResourceLoader(__name__)  # pylint: disable=invalid-name


class ActiveTablefrXBlock(StudioEditableXBlockMixin, XBlock):
    """An XBlock with a tabular problem type that requires students to fill in some cells."""

    display_name = String(
        display_name='Nom d\'affichage',
        help='Le nom que Studio utilise pour ce module avancé.',
        scope=Scope.settings,
        default='ActiveTable Français'
    )
    content = String(
        display_name='Définition du tableau',
        help='La définition du tableau dans une syntaxe simili-Python. Veuillez noter que tout changement au tableau d\'un problème actif invalidera toutes les réponses des étudiants',
        scope=Scope.content,
        multiline_editor=True,
        resettable_editor=False,
        default=textwrap.dedent("""\
        [
            ['Colonne 1', 'Colonne 2'],
            ['Entrer "allo" ici:', Text(answer='allo')],
            [42, Numeric(answer=42, tolerance=0.0)],
        ]
        """)
    )
    help_text = String(
        display_name='Aide',
        help='Le texte affiché quand on clique sur le bouton "+aide". Si vous enlevez le '
        'texte d\'aide, la fonction d\'aide sera désactivée.',
        scope=Scope.content,
        multiline_editor=True,
        resettable_editor=False,
        default='Remplissez les cellules surlignées avec les bonnes réponses. '
        'Quand vous aurez terminé, vous pourrez vérifier vos réponses en utilisant le bouton sous le tableau.',
    )
    column_widths = String(
        display_name='Largeur des colonnes',
        help='Définit la largeur des colonnes en pixels. Les valeurs doivent être une liste simili-Python de '
        'valeurs numériques. La largeur totale de la table ne doit pas dépasser 800. '
        'Si vous omettez cette valeur, vous obtiendrez des colonnes de largeur égale d\'une largeur totale de 800 pixels.',
        scope=Scope.content,
        resettable_editor=False,
    )
    row_heights = String(
        display_name='Hauteur des colonnes',
        help='Définit les hauteurs des lignes en pixels. Les valeurs doivent être une liste simili-Python de '
        'valeurs numériques. Les lignes peuvent augmenter plus que la valeur spécifiée si le texte dans certaines '
        'cellules de la ligne est assez long pour être enveloppé dans plus d\'une ligne.',
        scope=Scope.content,
        resettable_editor=False,
    )
    default_tolerance = Float(
        display_name='Tolérance par défaut',
        help='La tolérance en pourcentage utilisée pour les cellules de réponse numérique pour lesquelles '
        'vous n\'avez pas spécifié de tolérance explicite.',
        scope=Scope.content,
        default=1.0,
    )
    max_score = Float(
        display_name='Score maximum',
        help='Le nombre de points attribués aux étudiants lors de la résolution de tous les champs correctement.  '
        'Pour les tentatives partiellement correctes, le score sera calculé au prorata.',
        scope=Scope.settings,
        default=1.0,
    )
    max_attempts = Integer(
        display_name='Nombre maximum de tentatives',
        help='Définit le nombre de fois qu\'un élève peut tenter de répondre à ce problème. '
        'Si la valeur n\'est pas définie, des tentatives infinies sont autorisées.',
        scope=Scope.settings,
    )

    editable_fields = [
        'display_name',
        'content',
        'help_text',
        'column_widths',
        'row_heights',
        'default_tolerance',
        'max_score',
        'max_attempts',
    ]

    # Dictionary mapping cell ids to the student answers.
    answers = Dict(scope=Scope.user_state)
    # Dictionary mapping cell ids to Boolean values indicating whether the cell was answered
    # correctly at the last check.
    answers_correct = Dict(scope=Scope.user_state, default=None)
    # The number of points awarded.
    score = Float(scope=Scope.user_state)
    # The number of attempts used.
    attempts = Integer(scope=Scope.user_state, default=0)

    has_score = True

    @property
    def num_correct_answers(self):
        """The number of correct answers during the last check."""
        if self.answers_correct is None:
            return None
        return sum(self.answers_correct.itervalues())

    @property
    def num_total_answers(self):
        """The total number of answers during the last check."""
        if self.answers_correct is None:
            return None
        return len(self.answers_correct)

    def parse_fields(self):
        """Parse the user-provided fields into more processing-friendly structured data."""
        if self.content:
            self.thead, self.tbody = parse_table(self.content)
        else:
            self.thead = self.tbody = None
            return
        if self.column_widths:
            self._column_widths = parse_number_list(self.column_widths)
        else:
            self._column_widths = [800 / len(self.thead)] * len(self.thead)
        if self.row_heights:
            self._row_heights = parse_number_list(self.row_heights)
        else:
            self._row_heights = [36] * (len(self.tbody) + 1)

    def postprocess_table(self):
        """Augment the parsed table definition with further information.

        The additional information is taken from other content and student state fields.
        """
        self.response_cells = {}
        for row, height in zip(self.tbody, self._row_heights[1:]):
            row['height'] = height
            if row['index'] % 2:
                row['class'] = 'even'
            else:
                row['class'] = 'odd'
            for cell, cell.col_label in zip(row['cells'], self.thead):
                cell.id = 'cell_{}_{}'.format(row['index'], cell.index)
                cell.classes = ''
                if not cell.is_static:
                    self.response_cells[cell.id] = cell
                    cell.classes = 'active'
                    cell.value = self.answers.get(cell.id)
                    cell.height = height - 2
                    if isinstance(cell, NumericCell) and cell.abs_tolerance is None:
                        cell.set_tolerance(self.default_tolerance)

    def get_status(self):
        """Status dictionary passed to the frontend code."""
        return dict(
            answers_correct=self.answers_correct,
            num_correct_answers=self.num_correct_answers,
            num_total_answers=self.num_total_answers,
            score=self.score,
            max_score=self.max_score,
            attempts=self.attempts,
            max_attempts=self.max_attempts,
        )

    def student_view(self, context=None):
        """Render the table."""
        self.parse_fields()
        self.postprocess_table()

        context = dict(
            help_text=self.help_text,
            total_width=sum(self._column_widths) if self._column_widths else None,
            column_widths=self._column_widths,
            head_height=self._row_heights[0] if self._row_heights else None,
            thead=self.thead,
            tbody=self.tbody,
            max_attempts=self.max_attempts,
        )
        html = loader.render_template('templates/html/activetable.html', context)

        css_context = dict(
            correct_icon=self.runtime.local_resource_url(self, 'public/img/correct-icon.png'),
            incorrect_icon=self.runtime.local_resource_url(self, 'public/img/incorrect-icon.png'),
            unanswered_icon=self.runtime.local_resource_url(self, 'public/img/unanswered-icon.png'),
        )
        css = loader.render_template('templates/css/activetable.css', css_context)

        frag = Fragment(html)
        frag.add_css(css)
        frag.add_javascript(loader.load_unicode('static/js/src/activetable.js'))
        frag.initialize_js('ActiveTablefrXBlock', self.get_status())
        return frag

    def check_and_save_answers(self, data):
        """Common implementation for the check and save handlers."""
        if self.max_attempts and self.attempts >= self.max_attempts:
            # The "Check" button is hidden when the maximum number of attempts has been reached, so
            # we can only get here by manually crafted requests.  We simply return the current
            # status without rechecking or storing the answers in that case.
            return self.get_status()
        self.parse_fields()
        self.postprocess_table()
        answers_correct = {
            cell_id: self.response_cells[cell_id].check_response(value)
            for cell_id, value in data.iteritems()
        }
        # Since the previous statement executed without error, the data is well-formed enough to be
        # stored.  We now know it's a dictionary and all the keys are valid cell ids.
        self.answers = data
        return answers_correct

    @XBlock.json_handler
    def check_answers(self, data, unused_suffix=''):
        """Check the answers given by the student.

        This handler is called when the "Check" button is clicked.
        """
        self.answers_correct = self.check_and_save_answers(data)
        self.attempts += 1
        self.score = self.num_correct_answers * self.max_score / len(self.answers_correct)
        self.runtime.publish(self, 'grade', dict(value=self.score, max_value=self.max_score))
        return self.get_status()

    @XBlock.json_handler
    def save_answers(self, data, unused_suffix=''):
        """Save the answers given by the student without checking them."""
        self.check_and_save_answers(data)
        self.answers_correct = None
        return self.get_status()

    def validate_field_data(self, validation, data):
        """Validate the data entered by the user.

        This handler is called when the "Save" button is clicked in Studio after editing the
        properties of this XBlock.
        """
        def add_error(msg):
            """Add a validation error."""
            validation.add(ValidationMessage(ValidationMessage.ERROR, msg))
        try:
            thead, tbody = parse_table(data.content)
        except ParseError as exc:
            add_error('Problème avec la définition du tableau : ' + exc.message)
            thead = tbody = None
        if data.column_widths:
            try:
                column_widths = parse_number_list(data.column_widths)
            except ParseError as exc:
                add_error('Problem with column widths: ' + exc.message)
            else:
                if thead is not None and len(column_widths) != len(thead):
                    add_error(
                        'The number of list entries in the Column widths field must match the '
                        'number of columns in the table.'
                    )
        if data.row_heights:
            try:
                row_heights = parse_number_list(data.row_heights)
            except ParseError as exc:
                add_error('Problem with row heights: ' + exc.message)
            else:
                if tbody is not None and len(row_heights) != len(tbody) + 1:
                    add_error(
                        'The number of list entries in the Row heights field must match the number '
                        'of rows in the table.'
                    )

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("ActiveTablefrXBlock",
             """<vertical_demo>
                  <activetable url_name="basic">
                    [
                      ['Event', 'Year'],
                      ['French Revolution', Numeric(answer=1789)],
                      ['Krakatoa volcano explosion', Numeric(answer=1883)],
                      ["Proof of Fermat's last theorem", Numeric(answer=1994)],
                    ]
                  </activetable>
                </vertical_demo>
             """),
        ]
