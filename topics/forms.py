from django import forms

from core.models import Topic


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = [
            "name",
            "slug",  # generated?
            "description",
            "parent",  # Self Ref = Topic
            "templates",  # ?
            "path",  # Calculated
            "depth",  # Calculated?
        ]


# NOTE: should sluggify here in clean()...
