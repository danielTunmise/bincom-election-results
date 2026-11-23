"""
Models mapped onto the EXISTING tables from the Bincom dump.

`managed = False` tells Django: "this table already exists - never create,
alter or drop it". We map only the columns we need.

How the tables really link together (verified against the data):

    lga.lga_id            <--  ward.lga_id                  (ward belongs to an LGA)
    ward.uniqueid         <--  polling_unit.uniquewardid    (polling unit belongs to a ward)
    polling_unit.uniqueid <--  announced_pu_results.polling_unit_uniqueid

Gotchas that shaped these models:
  * lga.uniqueid and lga.lga_id are DIFFERENT numbers; other tables use lga_id.
  * ward.ward_id is only a per-LGA counter (it is 0 for every ward in LGAs
    31-35), so it can NOT identify a ward. ward.uniqueid is the real key.
  * announced_pu_results.polling_unit_uniqueid is a text column holding the
    polling unit's *uniqueid* (NOT polling_unit_id), so it is a CharField.
  * Unmapped columns such as ward.date_entered contain '0000-00-00', which
    Django cannot parse as a date - another reason to map only what we use.
"""
from django.db import models


class Lga(models.Model):
    uniqueid = models.AutoField(primary_key=True)
    # lga_id is what the ward table points to, so it acts as the "business key".
    # unique=True is only a declaration for Django (the table is unmanaged)
    # that lets a ForeignKey target this column.
    lga_id = models.IntegerField(unique=True)
    lga_name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "lga"
        ordering = ["lga_name"]

    def __str__(self):
        return self.lga_name


class Ward(models.Model):
    uniqueid = models.AutoField(primary_key=True)
    ward_id = models.IntegerField()        # per-LGA counter, NOT unique
    ward_name = models.CharField(max_length=50)
    # ward.lga_id column -> lga.lga_id
    lga = models.ForeignKey(
        Lga, to_field="lga_id", db_column="lga_id",
        on_delete=models.DO_NOTHING, related_name="wards",
    )

    class Meta:
        managed = False
        db_table = "ward"
        ordering = ["ward_name"]

    def __str__(self):
        return self.ward_name


class PollingUnit(models.Model):
    uniqueid = models.AutoField(primary_key=True)
    polling_unit_id = models.IntegerField()   # number of the unit inside its ward
    # Column `ward_id` = the ward's per-LGA counter (unreliable). It is named
    # ward_number in Python because the ForeignKey below already owns `ward_id`.
    ward_number = models.IntegerField(db_column="ward_id")
    lga_id = models.IntegerField()            # copy of lga.lga_id
    # polling_unit.uniquewardid column -> ward.uniqueid  (the reliable link)
    ward = models.ForeignKey(
        Ward, db_column="uniquewardid",
        on_delete=models.DO_NOTHING, related_name="polling_units",
    )
    polling_unit_number = models.CharField(max_length=50, null=True, blank=True)
    polling_unit_name = models.CharField(max_length=50, null=True, blank=True)
    entered_by_user = models.CharField(max_length=50, null=True, blank=True)
    user_ip_address = models.CharField(max_length=50, null=True, blank=True)
    # polling_unit.date_entered is deliberately NOT mapped: some rows hold
    # '0000-00-00 00:00:00' which Django cannot read (it would crash the page).
    # The column is nullable, so new rows simply leave it empty.

    class Meta:
        managed = False
        db_table = "polling_unit"
        ordering = ["polling_unit_name", "polling_unit_number"]

    @property
    def label(self):
        """Text shown in dropdowns, e.g. 'Igini Primary School (DT3403005)'."""
        name = self.polling_unit_name or "Unnamed polling unit"
        if self.polling_unit_number:
            return f"{name} ({self.polling_unit_number})"
        return name


class Party(models.Model):
    id = models.AutoField(primary_key=True)
    partyid = models.CharField(max_length=11)      # abbreviation e.g. 'PDP'
    partyname = models.CharField(max_length=11)

    class Meta:
        managed = False
        db_table = "party"
        ordering = ["id"]

    def __str__(self):
        return self.partyname

    @property
    def result_key(self):
        """
        The abbreviation as stored in the results tables. Those columns were
        char(4) in MySQL, so 'LABOUR' was saved as 'LABO'.
        """
        return self.partyid[:4]


class PuResult(models.Model):
    """One row = the score of ONE party at ONE polling unit."""
    result_id = models.AutoField(primary_key=True)
    # Text column that holds polling_unit.uniqueid (as a string).
    polling_unit_uniqueid = models.CharField(max_length=50)
    party_abbreviation = models.CharField(max_length=4)
    party_score = models.IntegerField()
    entered_by_user = models.CharField(max_length=50)
    date_entered = models.DateTimeField()
    user_ip_address = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "announced_pu_results"


class LgaResult(models.Model):
    """Officially announced LGA result - only used as a comparison on page 2."""
    result_id = models.AutoField(primary_key=True)
    lga_name = models.CharField(max_length=50)     # NOTE: actually holds the lga_id as text!
    party_abbreviation = models.CharField(max_length=4)
    party_score = models.IntegerField()

    class Meta:
        managed = False
        db_table = "announced_lga_results"
