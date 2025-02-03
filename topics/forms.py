from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms

from core.models import Topic


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = [
            "name",
            "slug",
            "description",
            "parent",
            "templates",
            "path",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group"),
                Column("slug", css_class="form-group"),
                Column("description", css_class="form-group"),
                Column("parent", css_class="form-group"),
                Column("path", css_class="form-group"),
                css_class="form-row",
            ),
            Row(Column("templates", css_class="form-group"), css_class="form-row"),
            Submit(
                "submit",
                "Save",
                css_class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600",
            ),
        )
