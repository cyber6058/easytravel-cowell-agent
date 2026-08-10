# 說明會產品區域確認設計

日期：2026-08-10

## 問題與決策

新魅力正式產品頁的卡片契約可成功辨識，但產品名稱不一定包含「大阪」、
「東北」或「北海道」。產品代碼前綴也不是區域的可靠代理，因此 parser 不得
用名稱片段、代碼前綴、航點或行程內容猜測產品區域。

採用的決策是：來源能唯一明示區域時沿用來源值；來源沒有明示區域時保留空值，
由 OP 從第一階段允許的三個值中明確確認。未知值與互相矛盾的值一律 fail closed。

## 範圍

本次只處理 `travel_briefing` 的產品區域解析、來源合併與 OP 確認，不新增 JMA、
Word COM、語音、LINE、Cowell 或其他外部整合。第一階段允許值固定為：

- `大阪`
- `東北`
- `北海道`

不建立產品代碼前綴表，也不從航班目的地推論產品區域。

## 資料流程

### 官網與 PDF parser

既有公開 seam 維持不變：

- `parse_newamazing_html(html, source_url, retrieved_at)`
- PDF parser 的既有公開入口

區域解析有三種結果：

1. 名稱恰好包含一個允許區域：回傳該值。
2. 名稱未包含任何允許區域：回傳空字串，讓 merge 建立待確認狀態。
3. 名稱同時包含兩個以上允許區域：回報 `PARSE_CONTRACT_CHANGED`，不任選其一。

parser 仍須完整驗證產品代碼、日期、航班、每日行程與其他說明；區域缺漏不能
放寬其他 fail-closed 契約。

### 來源合併

`merge_briefing_sources(...)` 按下列規則處理區域：

- URL-only 且官網區域空白：保留 `product.region=""`，新增一個
  `SOURCE_REGION_MISSING` warning，並新增黃色待確認欄位 `product_region`。
- URL+PDF 且官網區域空白、PDF 有合法區域：保留 PDF 區域，新增 warning，
  不建立 blocking conflict，也不要求 OP 重填。
- PDF 與官網各有不同的非空合法區域：維持既有 blocking conflict。
- 兩個來源都沒有區域：保留空值並要求 OP 確認一次，不重複 warning 或欄位。

既有九個 OP 欄位不改名、不改順序；`product_region` 只在區域缺漏時動態附加。
因此既有已明確辨識區域的草稿序列化內容不會無故改變。

### OP 確認

`apply_op_values(draft, payload)` 仍是唯一確認入口，並繼續要求目前的 `draft_id`。
只有草稿已包含待確認的 `product_region` 欄位時，payload 才能提交此值。

- 值為 `大阪`、`東北` 或 `北海道`：更新 `draft.product.region`，將該 OP 欄位標記為
  `source="OP"`、`confirmed=true`、移除黃色 highlight，並重算 `draft_id`。
- 空白、placeholder、未知區域或草稿未要求卻提交此欄位：回報
  `BriefingInputError`。

確認區域後狀態回到既有的 `DRAFT_READY` 判定；本設計不繞過其他 OP 欄位、衝突或
最終 `CONFIRMED` 關卡。`OpField` 保存這個值的 OP provenance；產品的既有來源清單
不偽裝成官網提供了該區域。

## 錯誤處理與安全

- 不建立 `OSA → 大阪`、`TOH → 東北` 或其他未由正式來源證明的映射。
- 不因產品區域缺漏而發出額外網路請求。
- 不保存 live HTML、產品頁內容或旅客資料。
- 多區域、未知 OP 值、過期 `draft_id` 與非預期欄位全部 fail closed。
- 修復後的正式頁重驗仍是一次性、無 redirect、無 retry 的獨立網路關卡。

## 測試 seam 與驗收

測試只走三個公開 seam，不直接測 private helper：

1. `parse_newamazing_html`：沒有區域關鍵字時成功回傳空區域；同時出現兩個區域時
   回報 `PARSE_CONTRACT_CHANGED`。
2. `merge_briefing_sources`：URL-only 建立單一 warning 與動態 OP 欄位；URL+PDF
   保留 PDF 區域且不建立假衝突；兩個非空值不一致仍 blocked。
3. `apply_op_values`：只接受目前草稿要求的三個允許值，更新產品、欄位與
   `draft_id`；未知值、非預期欄位及過期決定均拒絕。

完成條件：針對性測試先紅後綠、完整離線 pytest 通過、compileall 與
`git diff --check` 通過、沒有 live 原始內容進入 Git。正式頁 GET 的成功是後續
獨立驗收，不是離線 implementation commit 的完成條件。

## 未採用方案

- 產品代碼前綴映射：自動化程度高，但前綴已被證明不能可靠代表航點或區域。
- 從航班或每日行程推論：旅遊產品可能跨區或使用鄰近機場，仍屬猜測。
- 強制提供 PDF：安全但破壞已核准的 URL-only 工作流。
