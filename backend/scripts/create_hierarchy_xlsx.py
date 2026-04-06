"""Generate the organisation_hierarchy.xlsx seed file.

Run once to create/update the XLSX under backend/data/.
Each row describes one organisation unit with its parent linkage.

Columns: level, name, parent_name
  - level: one of leitung, landesverband, regionalstelle, ortsverband
  - name: display name of the unit
  - parent_name: display name of the parent unit (empty for top‑level)
"""

from pathlib import Path

from openpyxl import Workbook

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ROWS: list[tuple[str, str, str]] = [
    # level, name, parent_name
    ("leitung", "THW-Leitung", ""),
    # Landesverbände
    ("landesverband", "LV Bayern", "THW-Leitung"),
    ("landesverband", "LV Nordrhein-Westfalen", "THW-Leitung"),
    # Regionalstellen under LV Bayern
    ("regionalstelle", "Rst München", "LV Bayern"),
    ("regionalstelle", "Rst Nürnberg", "LV Bayern"),
    # Regionalstellen under LV NRW
    ("regionalstelle", "Rst Köln", "LV Nordrhein-Westfalen"),
    ("regionalstelle", "Rst Düsseldorf", "LV Nordrhein-Westfalen"),
    # Ortsverbände under Rst München
    ("ortsverband", "OV München-Ost", "Rst München"),
    ("ortsverband", "OV München-West", "Rst München"),
    ("ortsverband", "OV Freising", "Rst München"),
    # Ortsverbände under Rst Nürnberg
    ("ortsverband", "OV Nürnberg-Nord", "Rst Nürnberg"),
    ("ortsverband", "OV Erlangen", "Rst Nürnberg"),
    # Ortsverbände under Rst Köln
    ("ortsverband", "OV Köln-Mitte", "Rst Köln"),
    ("ortsverband", "OV Bonn", "Rst Köln"),
    # Ortsverbände under Rst Düsseldorf
    ("ortsverband", "OV Düsseldorf-Nord", "Rst Düsseldorf"),
    ("ortsverband", "OV Essen", "Rst Düsseldorf"),
]


def main() -> None:
    """Generate the organisation_hierarchy.xlsx seed file under backend/data/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Hierarchy"
    ws.append(["level", "name", "parent_name"])
    for row in ROWS:
        ws.append(list(row))
    # Auto‑size columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col) + 2
        ws.column_dimensions[col[0].column_letter].width = max_len  # type: ignore[union-attr]
    dest = DATA_DIR / "organisation_hierarchy.xlsx"
    wb.save(dest)
    print(f"Created {dest}")


if __name__ == "__main__":
    main()
