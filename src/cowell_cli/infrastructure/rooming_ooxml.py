from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from ..errors import ValidationError


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
W = f"{{{WORD_NS}}}"
X = f"{{{SHEET_NS}}}"
R = f"{{{REL_NS}}}"


@dataclass(frozen=True, slots=True)
class OoxmlCell:
    text: str
    vertical_merge: str | None = None


@dataclass(frozen=True, slots=True)
class OoxmlTable:
    rows: tuple[tuple[OoxmlCell, ...], ...]


@dataclass(frozen=True, slots=True)
class OoxmlDocument:
    tables: tuple[OoxmlTable, ...]
    searchable_text: str


def read_ooxml(path: Path) -> OoxmlDocument:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".xlsx":
        return _read_xlsx(path)
    raise ValidationError(
        "Rooming list must be a .docx or .xlsx file",
        {"path": str(path), "suffix": suffix},
    )


def _read_docx(path: Path) -> OoxmlDocument:
    try:
        with ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
    except (BadZipFile, KeyError, ET.ParseError) as error:
        raise ValidationError("Invalid DOCX rooming list", {"path": str(path)}) from error

    tables: list[OoxmlTable] = []
    for table_node in root.findall(f".//{W}tbl"):
        rows: list[tuple[OoxmlCell, ...]] = []
        for row_node in table_node.findall(f"./{W}tr"):
            cells: list[OoxmlCell] = []
            for cell_node in row_node.findall(f"./{W}tc"):
                text = "".join(
                    node.text or "" for node in cell_node.findall(f".//{W}t")
                ).strip()
                merge_node = cell_node.find(f"./{W}tcPr/{W}vMerge")
                merge = None
                if merge_node is not None:
                    merge = merge_node.get(f"{W}val", "continue")
                cells.append(OoxmlCell(text=text, vertical_merge=merge))
            rows.append(tuple(cells))
        tables.append(OoxmlTable(rows=tuple(rows)))

    searchable = "\n".join(
        "".join(node.text or "" for node in paragraph.findall(f".//{W}t"))
        for paragraph in root.findall(f".//{W}p")
    )
    return OoxmlDocument(tables=tuple(tables), searchable_text=searchable)


def _read_xlsx(path: Path) -> OoxmlDocument:
    try:
        with ZipFile(path) as archive:
            shared = _xlsx_shared_strings(archive)
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {
                rel.get("Id", ""): rel.get("Target", "")
                for rel in rels.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
            }
            tables: list[OoxmlTable] = []
            for sheet in workbook.findall(f".//{X}sheet"):
                target = targets.get(sheet.get(f"{R}id", ""), "")
                if not target:
                    continue
                member = target.lstrip("/")
                if not member.startswith("xl/"):
                    member = f"xl/{member}"
                sheet_root = ET.fromstring(archive.read(member.replace("\\", "/")))
                tables.append(_xlsx_sheet_table(sheet_root, shared))
    except (BadZipFile, KeyError, ET.ParseError) as error:
        raise ValidationError("Invalid XLSX rooming list", {"path": str(path)}) from error

    searchable = "\n".join(
        " | ".join(cell.text for cell in row)
        for table in tables
        for row in table.rows
    )
    return OoxmlDocument(tables=tuple(tables), searchable_text=searchable)


def _xlsx_shared_strings(archive: ZipFile) -> tuple[str, ...]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return ()
    return tuple(
        "".join(node.text or "" for node in item.findall(f".//{X}t"))
        for item in root.findall(f".//{X}si")
    )


def _xlsx_sheet_table(root: ET.Element, shared: tuple[str, ...]) -> OoxmlTable:
    rows: list[tuple[OoxmlCell, ...]] = []
    for row_node in root.findall(f".//{X}sheetData/{X}row"):
        values: dict[int, str] = {}
        for cell_node in row_node.findall(f"./{X}c"):
            reference = cell_node.get("r", "")
            column = _column_index(reference)
            cell_type = cell_node.get("t", "")
            value_node = cell_node.find(f"./{X}v")
            if cell_type == "inlineStr":
                value = "".join(
                    node.text or "" for node in cell_node.findall(f".//{X}t")
                )
            elif value_node is None:
                value = ""
            elif cell_type == "s":
                index = int(value_node.text or "0")
                value = shared[index] if index < len(shared) else ""
            else:
                value = value_node.text or ""
            values[column] = value.strip()
        if values:
            width = max(values) + 1
            rows.append(tuple(OoxmlCell(values.get(index, "")) for index in range(width)))
    return OoxmlTable(rows=tuple(rows))


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    if not letters:
        return 0
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1
