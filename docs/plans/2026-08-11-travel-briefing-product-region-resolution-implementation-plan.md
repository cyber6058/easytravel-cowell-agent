# 說明會產品區域確認實作計畫

日期：2026-08-11
依據：`docs/specs/2026-08-10-travel-briefing-product-region-resolution-design.md`
狀態：規格已由使用者通過；下列垂直切片已於 2026-08-11 完成。

## 邊界

- 只修改 NewAmazing 區域解析、來源 merge 與 OP values。
- 公開測試 seam 固定為 `parse_newamazing_html`、`merge_briefing_sources`、
  `apply_op_values`。
- 不新增代碼前綴或航點推論，不發出 live GET，不開始 Task 6。

## Slice 1：parser 保留缺漏並拒絕歧義

1. 在 `tests/unit/travel_briefing/test_newamazing.py` 新增名稱沒有允許區域時
   `product.region == ""` 的 failing test。
2. 只修改 `src/travel_briefing/adapters/newamazing.py`，讓零個區域回傳空值。
3. 新增名稱同時含兩個允許區域時回報 `PARSE_CONTRACT_CHANGED` 的測試並確認通過。

驗證：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_newamazing.py -q
```

## Slice 2：merge 建立動態 OP 欄位

1. 在 `tests/unit/travel_briefing/test_merge.py` 新增 URL-only 缺區域的 failing test；
   固定單一 `SOURCE_REGION_MISSING` warning 與尾端 `product_region` 黃色欄位。
2. 修改 `src/travel_briefing/{merge,op_values}.py`，讓
   `build_missing_op_fields()` 可選擇附加動態區域欄位。
3. 新增 URL+PDF 的 failing test；官網空白時保留 PDF 區域、不建立區域 conflict，
   只留下單一 warning。
4. 新增雙方非空區域不一致的 blocking regression test。

驗證：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_merge.py -q
```

## Slice 3：OP 確認更新產品區域

1. 在 `tests/unit/travel_briefing/test_op_values.py` 新增 failing test：草稿要求
   `product_region` 時，合法值更新產品與欄位並重算 `draft_id`。
2. 修改 `apply_op_values()`，只允許目前草稿存在的動態欄位，並只接受
   `大阪`、`東北`、`北海道`。
3. 新增未知值與未要求卻提交 `product_region` 的 fail-closed tests。

驗證：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_op_values.py -q
```

## Slice 4：完整驗證與交接

1. 執行三個針對性 test modules、compileall、完整 pytest、行寬與
   `git diff --check`。
2. 掃描 diff，確認沒有正式產品內容、live HTML、電話、email 或 PII。
3. 更新 `STATUS.md` 與原實作計畫，記錄實際輸出、commit、尚未執行的 live 驗證。
4. 建立本機 implementation commit；push 與下一次 live GET 各自等待明確核准。

## 完成紀錄

- 四個公開 parser／merge／OP-value test modules：`57 passed in 0.54s`。
- parser evidence 版本升為 `newamazing-html/3` 與 `pdf-itinerary/2`。
- 完整離線回歸：`258 passed, 2 skipped in 6.03s`；兩個 skip 為原有、需顯式
  opt-in 的 Hanhan／Yating 真實 integration tests。
- compileall、Python 行寬檢查及 `git diff --check` 通過。
- 離線實作階段未發出 live GET，未保存正式頁 HTML、live response 或 PII。

## Live 驗收紀錄

2026-08-11 經使用者另行明確核准，對同一正式產品 URL 執行恰好一次不 redirect、
不 retry 的唯讀 GET。HTTP `200`、response `98,464` bytes、SHA-256
`a4077429981bb47c6cbfccae113901a1b3d66b9a4cc069c35fa7e12a8470f216`；
`newamazing-html/3` 解析 2 航班、5 天與 5 項其他說明，merge 產生單一
`SOURCE_REGION_MISSING` warning、單一 `product_region` OP 欄位與
`DRAFT_READY`，結果為 `PASS`。沒有保存正式頁 HTML、live response 或 PII；
本次 GET 授權已用畢。
