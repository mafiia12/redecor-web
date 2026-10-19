"""CSV / XLSX export helpers shared by every admin export (readiness, enquiries)."""

import csv
import io

from fastapi.responses import Response

_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(v):
    """Formula-injection protection: text starting with = + - @ (or tab/CR) is prefixed with an apostrophe,
    so spreadsheet programs show it as text instead of running it."""
    if isinstance(v, str) and v.startswith(_DANGEROUS):
        return "'" + v
    return v


def export(rows: list[dict], columns: list[str], filename: str, fmt: str) -> Response:
    if fmt == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(columns)
        for r in rows:
            ws.append([safe_cell(r.get(c, "")) for c in columns])
        buf = io.BytesIO()
        wb.save(buf)
        return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'})
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(columns)
    for r in rows:
        w.writerow([safe_cell(r.get(c, "")) for c in columns])
    # UTF-8 with BOM so Excel opens Arabic text correctly
    return Response(out.getvalue().encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'})
