"""Word cloud is ungraded xblock used by students to
generate and view word cloud..

On the client side we show:
If student does not yet anwered - five text inputs.
If student have answered - words he entered and cloud.

Stunent can change his answer.
"""

import cgi
import json
import logging
import re
from copy import deepcopy
from collections import OrderedDict

from lxml import etree
from pkg_resources import resource_string

from xmodule.x_module import XModule
from xmodule.stringify import stringify_children
from xmodule.mako_module import MakoModuleDescriptor
from xmodule.xml_module import XmlDescriptor
from xblock.core import Scope, String, Object, Boolean, List, Integer

log = logging.getLogger(__name__)


class WordCloudFields(object):
    # Name of poll to use in links to this poll
    display_name = String(help="Display name for this module", scope=Scope.settings)
    num_inputs = Integer(help="Number of inputs", scope=Scope.settings, default=5)
    num_top_words = Integer(help="Number of inputs", scope=Scope.settings, default=250)

    submitted = Boolean(help="Whether this student has posted words to the cloud", scope=Scope.student_state, default=False)
    student_words= List(help="Student answer", scope=Scope.student_state, default=[])

    all_words = Object(help="All possible words from other students", scope=Scope.content)
    top_words = Object(help="Top N words for word cloud", scope=Scope.content)

class WordCloudModule(WordCloudFields, XModule):
    """WordCloud Module"""
    js = {
      'coffee': [resource_string(__name__, 'js/src/javascript_loader.coffee')],
      'js': [resource_string(__name__, 'js/src/word_cloud/logme.js'),
             resource_string(__name__, 'js/src/word_cloud/word_cloud.js'),
             resource_string(__name__, 'js/src/word_cloud/word_cloud_main.js')]
         }
    css = {'scss': [resource_string(__name__, 'css/word_cloud/display.scss')]}
    js_module_name = "WordCloud"

    def get_state_json(self):
        if self.submitted:
            return json.dumps({
                'status': 'success',
                'student_words': self.student_words,
                'top_words': self.prepare_words(self.top_words)
            })
        else:
            return json.dumps({})

    def good_word(self, word):
        return word.strip().lower()

        # TODO: use or remove
        # real_words = re.findall('\w+', word)
        # if real_words:
        #     return real_words[0].lower()

    def prepare_words(self, words):
        """Convert words dictionary more handy for client."""
        return [{'text': word, 'size': count} for
            word, count in words.iteritems()]

    def top_dict(self, dict_obj, amount):
        return dict(
            sorted(
                dict_obj.iteritems(),
                key=lambda x: x[1],
                reverse=True
            )[:amount]
        )

    def handle_ajax(self, dispatch, get):
        """Ajax handler.

        Args:
            dispatch: string request slug
            get: dict request get parameters

        Returns:
            json string
        """
        if dispatch == 'submit':
            if self.submitted:
                return json.dumps({
                    'status': 'fail',
                    'error': 'You have already post your data.'
                })

            # Student words from client.
            raw_student_words = json.loads(get.lists()[0][0])['data']
            student_words = filter(None, map(self.good_word, raw_student_words))

            if not student_words:
                return json.dumps({
                    'status': 'fail',
                    'error': 'Empty students words.'
                })

            self.student_words = student_words

            # FIXME: fix this, when xblock will support mutable types.
            # Now we use this hack.
            # speed issues
            temp_all_words = self.all_words

            self.submitted = True

            # Save in all_words.
            for word in self.student_words:
                if word in temp_all_words:
                    temp_all_words[word] += 1
                else:
                    temp_all_words[word] = 1

            # Update top_words
            self.top_words = self.top_dict(temp_all_words,
                int(self.num_top_words))

            self.all_words = temp_all_words

            return self.get_state_json()

        elif dispatch == 'get_state':
            return self.get_state_json()
        else:
            return json.dumps({
                    'status': 'fail',
                    'error': 'Unknown Command!'
                })

    def get_html(self):
        """Renders parameters to template."""
        params = {
                  'element_id': self.location.html_id(),
                  'element_class': self.location.category,
                  'ajax_url': self.system.ajax_url,
                  'configuration_json': self.get_state_json(),
                  'num_inputs': int(self.num_inputs),
                  }
        self.content = self.system.render_template('word_cloud.html', params)
        return self.content


class WordCloudDescriptor(WordCloudFields, MakoModuleDescriptor, XmlDescriptor):
    _tag_name = 'word_cloud'

    module_class = WordCloudModule
    template_dir_name = 'word_cloud'
    stores_state = True

    @classmethod
    def definition_from_xml(cls, xml_object, system):
        """Pull out the data into dictionary.

        Args:
            xml_object: xml from file.
            system: `system` object.

        Returns:
            (definition, children) - tuple

        """
        definition = {}
        children = []

        return (definition, children)

    def definition_to_xml(self, resource_fs):
        """Return an xml element representing to this definition."""
        xml_str = '<{tag_name} />'.format(tag_name=self._tag_name)
        xml_object = etree.fromstring(xml_str)
        xml_object.set('display_name', self.display_name)
        xml_object.set('num_inputs', self.num_inputs)

        return xml_object
