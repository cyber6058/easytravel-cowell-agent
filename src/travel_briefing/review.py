from __future__ import annotations

import re

from .models import BriefingDraft, SourceEvidence


_MOBILE_PHONE = re.compile(
    r"(?<!\d)(?:(?:\+?886)[-\s]?)?0?9\d{2}(?:[-\s]?\d){6}(?!\d)"
)
_LANDLINE_PHONE = re.compile(r"(?<!\d)0\d{1,2}(?:[-\s]?\d){6,8}(?!\d)")


def render_review(draft: BriefingDraft) -> str:
    lines = [
        "# 說明會資料審核",
        "",
        f"- Draft ID：`{draft.draft_id}`",
        f"- 狀態：`{draft.status.value}`",
        f"- 產生時間：`{draft.generated_at}`",
        "",
        "## 來源",
        "",
        "| ID | 類型 | 位置 | 擷取時間 |",
        "| --- | --- | --- | --- |",
    ]
    for source in draft.sources:
        lines.append(
            "| "
            + " | ".join(
                (
                    _cell(source.source_id),
                    _cell(source.kind),
                    _cell(_display_location(source)),
                    _cell(source.retrieved_at),
                )
            )
            + " |"
        )
    if not draft.sources:
        lines.append("| 無 | 無 | 無 | 無 |")

    lines.extend(
        (
            "",
            "## OP 欄位",
            "",
            "| 欄位 | 值 | 已確認 | 標示 |",
            "| --- | --- | --- | --- |",
        )
    )
    for field in draft.op_fields:
        value = (
            "[電話已遮蔽]"
            if "phone" in field.name.casefold()
            else redact_sensitive_text(field.value)
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    _cell(field.name),
                    _cell(value),
                    "是" if field.confirmed else "否",
                    _cell(field.highlight or "無"),
                )
            )
            + " |"
        )
    if not draft.op_fields:
        lines.append("| 無 | 無 | 否 | 無 |")

    lines.extend(("", "## 衝突", ""))
    sources = {source.source_id: source for source in draft.sources}
    if not draft.conflicts:
        lines.append("無。")
    for conflict in draft.conflicts:
        lines.extend(
            (
                f"### `{_inline(conflict.field)}`",
                "",
                f"- 嚴重度：`{_inline(conflict.severity)}`",
                (
                    "- 來源 A："
                    f"{_source_description(conflict.source_a, sources)}；"
                    f"值：{_inline(conflict.value_a)}"
                ),
                (
                    "- 來源 B："
                    f"{_source_description(conflict.source_b, sources)}；"
                    f"值：{_inline(conflict.value_b)}"
                ),
                (
                    f"- 決定：`{_inline(conflict.decision)}`；"
                    f"決定者：`{_inline(conflict.decided_by)}`"
                    if conflict.decision
                    else "- OP 問題：請 OP 決定採用來源 A 或來源 B。"
                ),
                "",
            )
        )

    lines.extend(("## 提醒", ""))
    if not draft.warnings:
        lines.append("無。")
    for warning in draft.warnings:
        source_ids = ", ".join(warning.source_ids) or "無"
        lines.append(
            f"- `{_inline(warning.code)}`：{_inline(warning.message)} "
            f"（來源：{_inline(source_ids)}）"
        )
    return "\n".join(lines).rstrip() + "\n"


def redact_sensitive_text(value: str) -> str:
    redacted = _MOBILE_PHONE.sub("[電話已遮蔽]", value)
    return _LANDLINE_PHONE.sub("[電話已遮蔽]", redacted)


def _source_description(
    source_id: str,
    sources: dict[str, SourceEvidence],
) -> str:
    source = sources.get(source_id)
    if source is None:
        return f"`{_inline(source_id)}`（來源證據缺失）"
    return (
        f"`{_inline(source.source_id)}`，"
        f"{_inline(_display_location(source))}，"
        f"擷取於 `{_inline(source.retrieved_at)}`"
    )


def _display_location(source: SourceEvidence) -> str:
    location = source.location
    if source.kind != "pdf_page":
        return location
    path, separator, fragment = location.partition("#")
    name = re.split(r"[\\/]", path)[-1]
    return name + (separator + fragment if separator else "")


def _cell(value: str) -> str:
    return _inline(value).replace("|", "\\|")


def _inline(value: str) -> str:
    return redact_sensitive_text(str(value)).replace("\r", " ").replace("\n", " ")
