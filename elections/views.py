"""
Views for the three pages and the two JSON endpoints.

Page 1  polling_unit_result : result of ONE polling unit
Page 2  lga_total           : sum of all polling-unit results in an LGA
Page 3  add_polling_unit    : form to store results for a new polling unit
"""
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import NewPollingUnitForm
from .models import Lga, LgaResult, Party, PollingUnit, PuResult, Ward


# ---------------------------------------------------------------- helpers

def sum_by_party(results):
    """
    GROUP BY party_abbreviation on a queryset of PuResult rows.
    Returns {'PDP': {'total': 1234, 'entries': 1}, ...}.
    `entries` = how many rows were added up (normally 1; >1 means the dump
    holds several rows for that party at that polling unit).
    """
    rows = results.values("party_abbreviation").annotate(
        total=Sum("party_score"), entries=Count("result_id")
    )
    return {r["party_abbreviation"]: r for r in rows}


def lga_for_polling_unit_ids(lga):
    """All polling-unit uniqueids in an LGA, as strings (the results table stores them as text)."""
    ids = PollingUnit.objects.filter(ward__lga=lga).values_list("uniqueid", flat=True)
    return [str(i) for i in ids]


def to_int_or_none(value):
    """'12' -> 12; '', None or 'abc' -> None. Keeps the views safe from bad query strings."""
    return int(value) if value and value.isdigit() else None


# ------------------------------------------------- JSON endpoints (dropdowns)

def api_wards(request):
    """GET /api/wards/?lga=<lga_id>  ->  [{"id": ..., "name": ...}, ...]"""
    lga_id = to_int_or_none(request.GET.get("lga"))
    wards = Ward.objects.filter(lga_id=lga_id) if lga_id is not None else Ward.objects.none()
    return JsonResponse([{"id": w.uniqueid, "name": w.ward_name} for w in wards], safe=False)


def api_polling_units(request):
    """GET /api/polling-units/?ward=<ward uniqueid>  ->  [{"id": ..., "name": ...}, ...]"""
    ward_id = to_int_or_none(request.GET.get("ward"))
    units = PollingUnit.objects.filter(ward_id=ward_id) if ward_id is not None else PollingUnit.objects.none()
    return JsonResponse([{"id": u.uniqueid, "name": u.label} for u in units], safe=False)


# ------------------------------------------------------- Page 1: one unit

def polling_unit_result(request):
    """Pick LGA -> Ward -> Polling unit, then show that unit's party scores."""
    context = {"lgas": Lga.objects.all(), "unit": None, "rows": [], "grand_total": 0}

    unit_id = to_int_or_none(request.GET.get("polling_unit"))
    if unit_id is not None:
        # select_related joins ward and LGA in one query. Placeholder rows in the
        # dump (no ward) are dropped automatically by that join.
        unit = PollingUnit.objects.select_related("ward__lga").filter(pk=unit_id).first()
        if unit is None:
            messages.error(request, "That polling unit could not be found.")
        else:
            sums = sum_by_party(PuResult.objects.filter(polling_unit_uniqueid=str(unit.uniqueid)))
            rows = []
            for party in Party.objects.all():          # keep the party-table order
                if party.result_key in sums:
                    row = sums.pop(party.result_key)
                    rows.append({"party": party.partyname, "score": row["total"], "entries": row["entries"]})
            for abbreviation, row in sums.items():     # results for a party missing from the party table
                rows.append({"party": abbreviation, "score": row["total"], "entries": row["entries"]})
            context.update(
                unit=unit, rows=rows,
                grand_total=sum(r["score"] for r in rows),
                # pre-select the dropdowns to match the unit being shown
                selected_lga=unit.ward.lga_id, selected_ward=unit.ward_id, selected_unit=unit.uniqueid,
            )
    return render(request, "elections/polling_unit_result.html", context)


# --------------------------------------------------------- Page 2: LGA total

def lga_total(request):
    """
    Total per party for one LGA = SUM of announced_pu_results over every
    polling unit in that LGA. (announced_lga_results is shown only as a
    clearly-labelled comparison column, never used for the total.)
    """
    context = {"lgas": Lga.objects.all(), "lga": None}

    lga_id = to_int_or_none(request.GET.get("lga"))
    if lga_id is not None:
        lga = Lga.objects.filter(lga_id=lga_id).first()
        if lga is None:
            messages.error(request, "That LGA could not be found.")
        else:
            unit_ids = lga_for_polling_unit_ids(lga)
            results = PuResult.objects.filter(polling_unit_uniqueid__in=unit_ids)
            sums = sum_by_party(results)
            # announced_lga_results.lga_name holds the lga_id as text
            announced = {r.party_abbreviation: r.party_score for r in LgaResult.objects.filter(lga_name=str(lga.lga_id))}

            rows = [
                {
                    "party": party.partyname,
                    "total": sums.get(party.result_key, {}).get("total", 0),
                    "announced": announced.get(party.result_key),
                }
                for party in Party.objects.all()
            ]
            context.update(
                lga=lga, rows=rows, selected_lga=lga.lga_id,
                grand_total=sum(r["total"] for r in rows),
                announced_total=sum(v for v in announced.values()),
                has_announced=bool(announced),
                units_total=len(unit_ids),
                units_with_results=results.values("polling_unit_uniqueid").distinct().count(),
            )
    return render(request, "elections/lga_total.html", context)


# ------------------------------------------------ Page 3: add a polling unit

def add_polling_unit(request):
    """Show the form (GET) or validate + save the new polling unit and all party scores (POST)."""
    # Bind the form only on POST (an empty POST must still show "required" errors).
    form = NewPollingUnitForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        ward, lga = data["ward"], data["lga"]
        now = timezone.now()
        who = {"entered_by_user": "web form", "date_entered": now,
               "user_ip_address": request.META.get("REMOTE_ADDR", "")}

        # All-or-nothing: if any insert fails, nothing is saved.
        with transaction.atomic():
            # number of this unit inside its ward = highest existing + 1
            last = PollingUnit.objects.filter(ward=ward).aggregate(m=Max("polling_unit_id"))["m"] or 0
            unit = PollingUnit.objects.create(
                polling_unit_id=last + 1,
                ward_number=ward.ward_id, lga_id=lga.lga_id, ward=ward,
                polling_unit_name=data["polling_unit_name"].strip(),
                polling_unit_number=data["polling_unit_number"].strip() or None,
                entered_by_user=who["entered_by_user"],
                user_ip_address=who["user_ip_address"],
            )
            PuResult.objects.bulk_create([
                PuResult(
                    polling_unit_uniqueid=str(unit.uniqueid),
                    party_abbreviation=party.result_key,
                    party_score=data[f"score_{party.id}"],
                    **who,
                )
                for party in form.parties
            ])

        messages.success(request, f"Saved! Results for '{unit.polling_unit_name}' ({len(form.parties)} parties) were stored.")
        # Redirect-after-POST: refreshing the page can't re-submit the form.
        return redirect(f"{reverse('polling_unit_result')}?polling_unit={unit.uniqueid}")

    return render(request, "elections/add_polling_unit.html", {"form": form})
