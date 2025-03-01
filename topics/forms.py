from crispy_forms.helper import FormHelper
from crispy_forms.layout import (HTML, Button, ButtonHolder, Column, Layout,
                                 Row, Submit)
from django import forms

from core.models import Topic


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = [
            "name",
            "description",
            "parent",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group"),
                Column("description", css_class="form-group"),
                Column("parent", css_class="form-group"),
                css_class="form-row",
            ),
            Row(
                ButtonHolder(
                    Submit(
                        "submit",
                        "Save",
                        css_class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600",
                    ),
                    HTML(
                        """<a href="{% url "topic-list" %}" class="px-4 py-3 bg-blue-500 text-white rounded hover:bg-blue-600">Cancel</a>"""
                    ),
                ),
            ),
        )
