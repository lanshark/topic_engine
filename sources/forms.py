from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms

from core.models import Source


class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = [
            "name",
            "active",
            "url",
            "source_type",
            "check_frequency",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group"),
                Column("url", css_class="form-group"),
                Column("active", css_class="form-group"),
                Column("source_type", css_class="form-group"),
                Column("check_frequency", css_class="form-group"),
                css_class="form-row",
            ),
            Submit(
                "submit",
                "Save",
                css_class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600",
            ),
        )
