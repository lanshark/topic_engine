from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms

from core.models import ModelConfig


class ModelConfigForm(forms.ModelForm):
    class Meta:
        model = ModelConfig
        fields = [
            "name",
            "description",
            "active",
            "topic",
            "training_examples",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group"),
                Column("description", css_class="form-group"),
                Column("active", css_class="form-group"),
                Column("topic", css_class="form-group"),
                Column("training_examples", css_class="form-group"),
                # Column("parameters", css_class="form-group"),
                css_class="form-row",
            ),
            Submit(
                "submit",
                "Save",
                css_class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600",
            ),
        )
