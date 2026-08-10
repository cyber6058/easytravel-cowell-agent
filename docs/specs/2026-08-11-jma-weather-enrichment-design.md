# JMA 天氣補充設計

日期：2026-08-11

## 問題與決策

說明會草稿需要日本行程逐日天氣，但來源只能是氣象廳（JMA），而且目前新魅力
URL-only 產品頁不提供每日住宿城市。系統不得從景點、航點或產品區域猜測城市。

採用的最小設計是：只有當 PDF 或其他既有明確來源提供每日城市時，才用唯一城市
映射查詢 JMA 預報區；城市空白、映射不唯一、日期超出預報範圍或 JMA 無法使用時，
該日顯示固定文字「尚無短期預報，請於出發前更新」，並保留安全草稿。

## 官方契約基線

2026-08-11 唯讀查閱 JMA 官方文件後，第一階段固定使用：

- `VPFD51`：府縣天氣預報，今天至明後日，通常每日 5、11、17 時發布；包含天氣、
  最高／最低溫與降水機率等資料。
- `VPFW50`：府縣週間天氣預報，發布翌日至第 7 日，每日發布 2 次；包含天氣、
  最高／最低溫與降水機率等資料。
- 兩者均為氣象廳防災資訊 XML，從公開 PULL 型「定時」Atom feed 發現電文。
- 實作者須以 entry 的產品代碼篩選 `VPFD51`／`VPFW50`，不得靠標題文字猜種類。
- XML 規格以 JMA 技術資料 Ver. 1.3、電文解說資料與正式 sample 為準；parser 不依賴
  展示網站 HTML，也不把「全內容輸出 stylesheet」嵌入產品。

JMA 明示公開 feed 可能停止或延遲，公開資訊不保證迅速且確實送達；因此它只作為
說明會輔助資訊，不能成為草稿產生的硬依賴。實際接線前須另行核准一次受限的
JMA read-only 驗證，本設計與離線實作都不包含該次請求。

官方參考：

- https://www.data.jma.go.jp/suishin/cgi-bin/catalogue/make_product_page.cgi?id=TenkiYoh
- https://www.data.jma.go.jp/suishin/cgi-bin/catalogue/make_product_page.cgi?id=ShukanYo
- https://xml.kishou.go.jp/xmlpull.html
- https://xml.kishou.go.jp/tec_material.html
- https://www.jma.go.jp/jma/en/copyright.html

## 範圍

Task 6 只新增 JMA XML parser、天氣選擇邏輯、明確城市到 JMA 預報區的靜態映射、
離線 fixtures 與測試。第一階段不新增 OP 每日城市欄位，不抓歷史平均，也不新增
第三方天氣來源、Word COM、語音、LINE、部署或排程。

預計檔案：

- `src/travel_briefing/adapters/jma.py`
- `src/travel_briefing/weather.py`
- `src/travel_briefing/data/jma_area_aliases.json`
- 對應的 synthetic VPFD51／VPFW50 fixtures 與公開 seam 測試

只使用 Python 標準函式庫 XML parser；不新增 JMA SDK 或網路依賴套件。

## 資料流與公開 seam

### XML 解析

adapter 接受呼叫端已取得的 XML bytes、`source_url` 與 `retrieved_at`，不自行發網路
請求。公開 seam 分別解析 VPFD51 與 VPFW50，輸出正規化候選資料：

- 產品代碼與 report status
- JMA 發布時間
- 預報區名稱與代碼
- 預報日期
- 天氣文字
- 最高／最低溫
- 降水機率（來源有值時）
- `source_url` 與 `retrieved_at`

產品代碼錯誤、XML 格式錯誤、必要時間軸無法對齊、區域重複且內容矛盾時，回報
明確 parser error，不猜值。來源沒有提供的單一氣象元素可保持空值，但不能錯配
其他日期或區域的值。

### 城市映射

`jma_area_aliases.json` 只保存人工確認的精確 alias 與唯一 JMA 預報區代碼。查詢前
可做既定的空白與 Unicode 正規化，但不做模糊比對、鄰近城市推論或產品區域推論。

- 恰好一個映射：可選取該預報區資料。
- 沒有映射：該日 unavailable，新增可審閱 warning。
- 多個映射或設定重複：fail closed，視為設定錯誤。
- 每日城市空白：直接 unavailable，不嘗試 JMA，也不新增猜測欄位。

第一批 alias 只能由 synthetic 測試所需的已確認案例組成；擴充真實城市清單需有
JMA 預報區證據與對應測試。

### 日期與來源優先

每個行程日只可得到一筆 `WeatherForecast`：

1. 先找同一預報區、同一日期的有效 VPFD51。
2. 若沒有，再找有效 VPFW50。
3. 同產品有多份電文時，取 `issued_at` 較新的；發布時間相同但內容矛盾時 fail
   closed，不靠 feed 順序任選。
4. 若兩種產品同時涵蓋同日，VPFD51 優先，因其為較短期來源；不得只因 VPFW50
   取得時間較新就覆蓋 VPFD51。

所有可用結果保留實際 `issued_at`、`retrieved_at` 與 `source_url`，供 review 與文件
出處使用。行程日以日本當地日期比對；naive datetime 或無法辨識時區的資料拒絕。

## 降級、顯示與歸因

下列任一情況都不阻止安全草稿繼續：城市缺漏、alias 未知、行程超過第 7 日、
JMA feed／XML 取得失敗、指定日期無資料、或單一預報元素缺值。

- 無法建立可信逐日預報時，`available=false`，顯示固定文字
  「尚無短期預報，請於出發前更新」。
- JMA 整體失敗只建立一則去重 warning；每日 unavailable 狀態仍可個別保存。
- 不把舊電文、歷史平均或另一城市資料當 fallback。
- 文件須標示「資料來源：日本氣象廳（JMA）」與資料發布／取得時間，並提示預報
  可能更新；不得呈現為保證。
- JMA 官網內容依其使用條款可在保留出處下利用，但第三方權利內容需排除；本功能
  只處理 JMA XML 欄位，不複製 logo、圖像或第三方素材。

## 測試與完成條件

離線 synthetic fixtures 至少覆蓋：

1. VPFD51 正常解析今天至明後日。
2. VPFW50 正常解析翌日至第 7 日。
3. overlap 時 VPFD51 勝出；同產品取較新發布時間。
4. 同時間矛盾內容、錯誤產品代碼、錯位時間軸與重複區域 fail closed。
5. 城市唯一映射成功；空白、未知與多重映射不猜值。
6. 超出範圍、JMA failure 與缺資料產生固定 unavailable 文字且草稿仍安全。
7. 正規化結果保留 source URL、issued/retrieved time 與 JMA attribution。

完成條件為針對性測試先紅後綠、完整離線 pytest 通過、compileall 與
`git diff --check` 通過，且 Git 不含任何 live JMA response。第一次正式 JMA
read-only 驗證、Word 文件渲染與端對端說明會產物都屬後續獨立核准關卡。

## 未採用方案

- 直接解析 JMA 展示網站 JSON／HTML：取得方便，但不是本設計核准的穩定 XML 契約。
- 用產品區域或景點猜城市：自動化較高，但可能把跨區行程套到錯誤預報。
- 沒城市就新增 Task 6 OP 欄位：會擴大人工流程；第一階段維持固定 unavailable。
- JMA 失敗就阻塞整份草稿：不符合說明會輔助資訊定位，也放大官方服務短暫中斷。
- 引入第三方 weather SDK：增加依賴與來源，超出 JMA-only 範圍。
