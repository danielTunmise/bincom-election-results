# Delta State 2011 Election Results (Bincom ICT developer test)

A small Django 5 / Python 3 app on top of a SQLite copy of the Bincom MySQL dump
(`bincom_test.sql`, dummy 2011 Delta State results).
Hierarchy: **State > LGA > Ward > Polling Unit**.

## The three pages

| Page | URL | What it does |
|------|-----|--------------|
| **Polling Unit Result** | `/` | Chained dropdowns LGA -> Ward -> Polling unit, then a table of party scores and a total. A unit with no results shows a friendly "No results recorded" message. |
| **LGA Total** | `/lga-total/` | Pick an LGA and see the **sum of all its polling-unit results** per party. The announced LGA result is shown beside it in a grey column labelled "for comparison only". |
| **Add New Result** | `/add-result/` | Pick LGA + ward, enter the polling unit name (and optional number) and a score for **every** party in the `party` table. Validated, saved in one transaction, then redirects to the new unit's result page with a success message. |

The dropdowns are filled by JavaScript from two small JSON endpoints:
`/api/wards/?lga=<lga_id>` and `/api/polling-units/?ward=<ward uniqueid>`.

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python import_mysql_dump.py       # builds db.sqlite3 from bincom_test.sql
# Windows PowerShell:  $env:DJANGO_DEBUG="1"      macOS/Linux:  export DJANGO_DEBUG=1
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. (`DJANGO_DEBUG=1` is only needed locally so Django serves the CSS/JS.)
Re-running `import_mysql_dump.py` resets the database to the original data.

## Project layout

```
import_mysql_dump.py          MySQL dump -> SQLite converter
config/                       settings.py (tiny), urls.py
elections/models.py           models mapped to the existing tables (managed = False)
elections/views.py            3 page views + 2 JSON views
elections/forms.py            form for page 3 (one score field per party, built dynamically)
elections/templates/          base.html (nav bar) + one template per page
elections/static/elections/   style.css, chained-dropdowns.js
```

## How the data is linked (checked against the real data)

```
lga.lga_id            <-- ward.lga_id
ward.uniqueid         <-- polling_unit.uniquewardid
polling_unit.uniqueid <-- announced_pu_results.polling_unit_uniqueid   (text column, NOT polling_unit_id)
```

## How the LGA total is calculated

1. Find every polling unit in the LGA: `polling_unit -> ward -> lga`.
2. Take all `announced_pu_results` rows whose `polling_unit_uniqueid` is one of those units.
3. `GROUP BY party_abbreviation` and `SUM(party_score)`.

In Django: `PuResult.objects.filter(polling_unit_uniqueid__in=ids).values("party_abbreviation").annotate(Sum("party_score"))`.
`announced_lga_results` is **never** used for the total, only for the comparison column. Its `lga_name`
column actually holds the `lga_id` as text, so that is how it is matched.

## Assumptions and data quirks (things worth knowing for the interview)

* **Placeholder polling units.** 170 of the 272 `polling_unit` rows are blank (`lga_id = 0`, `ward_id = 0`, no name). They have no ward, so they never appear in the dropdowns.
* **`ward.ward_id` is not unique.** It is a per-LGA counter (it is `0` for every ward in LGAs 31-35). A ward is therefore identified by `ward.uniqueid`, and a polling unit's ward is found through `polling_unit.uniquewardid`, which matches for all 102 real units.
* **LGA of a polling unit = the LGA of its ward.** One record (polling unit 16, "school in ethiope west") has `polling_unit.lga_id = 7` but sits in a ward of LGA 6 (Ethiope West). Using the ward keeps the dropdown hierarchy and the LGA total consistent.
* **`lga.uniqueid` differs from `lga.lga_id`.** Other tables use `lga_id`, so the dropdowns submit `lga_id`.
* **LABO vs LABOUR.** The results tables had `char(4)` party columns, so `LABOUR` is stored as `LABO`. Matching uses the first 4 letters of `party.partyid`, new rows are stored the same way, and the pages display the full party name.
* **Duplicate rows.** Polling unit 10 has two rows for each of six parties (different scores). They are added together and flagged "(2 entries added)" on page 1, so the LGA total is consistent with that.
* **Only 18 polling units (in 8 LGAs) have results.** Other LGAs show a total of 0 with a note. The announced LGA numbers are dummy data and are nowhere near the sums; that is expected.
* **Bad dates.** `polling_unit.date_entered`, `ward.date_entered` and `lga.date_entered` contain `0000-00-00`, which Django cannot parse, so those columns are not mapped in the models.
* **Page 3 rules.** Name and every score are required; scores must be whole numbers from 0 to 10,000,000. The ward must belong to the chosen LGA. A polling unit name already used in that ward, or an already-used number, is rejected to prevent accidental double submission.
* New rows are stamped `entered_by_user = "web form"` with the time and the client IP.
* No login is used (not requested), so anyone who can open the site can add results.
* Django's auth/admin/sessions apps are not installed, so Django creates no tables of its own. Success messages are stored in a cookie.
* `db.sqlite3` is git-ignored. It is generated from the dump, which is committed.

## Deploying

See the PythonAnywhere steps in [DEPLOY.md](DEPLOY.md).
