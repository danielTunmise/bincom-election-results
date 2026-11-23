"""
The form for page 3 (add a new polling unit with a score for EVERY party).

The party score fields are created dynamically in __init__, one per row of the
`party` table, so if a party is added to the table the form picks it up.
"""
from django import forms

from .models import Lga, Party, PollingUnit, Ward

MAX_SCORE = 10_000_000  # sanity limit so a typo like 99999999999 is rejected


class NewPollingUnitForm(forms.Form):
    lga = forms.ModelChoiceField(
        queryset=Lga.objects.all(),
        to_field_name="lga_id",   # the form submits lga.lga_id, not lga.uniqueid
        empty_label="-- Select LGA --",
        label="Local Government Area (LGA)",
    )
    # The <select> for wards is drawn by hand in the template and filled by
    # JavaScript, so here we only need to validate the submitted value.
    ward = forms.ModelChoiceField(queryset=Ward.objects.all(), label="Ward")
    polling_unit_name = forms.CharField(max_length=50, label="Polling unit name")
    polling_unit_number = forms.CharField(
        max_length=50, required=False, label="Polling unit number (optional)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parties = list(Party.objects.all())
        # One required, non-negative whole-number field per party.
        for party in self.parties:
            self.fields[f"score_{party.id}"] = forms.IntegerField(
                label=party.partyname, min_value=0, max_value=MAX_SCORE,
                widget=forms.NumberInput(attrs={"min": 0, "step": 1, "placeholder": "0"}),
            )

    def score_fields(self):
        """Bound score fields (in party order) for the template to loop over."""
        return [self[f"score_{party.id}"] for party in self.parties]

    def clean(self):
        """Checks that involve more than one field."""
        cleaned = super().clean()
        lga, ward = cleaned.get("lga"), cleaned.get("ward")
        name = cleaned.get("polling_unit_name")
        number = cleaned.get("polling_unit_number")

        # The ward must really belong to the chosen LGA.
        if lga and ward and ward.lga_id != lga.lga_id:
            self.add_error("ward", "This ward does not belong to the selected LGA.")
            return cleaned

        # Guard against saving the same polling unit twice by accident.
        if ward and name and PollingUnit.objects.filter(
            ward=ward, polling_unit_name__iexact=name.strip()
        ).exists():
            self.add_error("polling_unit_name", "A polling unit with this name already exists in this ward.")
        if number and PollingUnit.objects.filter(polling_unit_number__iexact=number.strip()).exists():
            self.add_error("polling_unit_number", "This polling unit number is already used.")
        return cleaned
