# 說明會口語稿契約

本文件定義 `travel_briefing.script_policy` 與
`travel_briefing.script_validation` 的第一版契約。口語稿可以調整銜接與重複內容，
但不得重新抓網站、查其他來源、推測缺值或改動已核准的事實。

## Narration input

`build_narration_input(BriefingDraft)` 產生
`briefing_narration_input` schema version 1。輸入必須保留 `draft_id`，並包含：

- 固定八段的 `sections` 與 marker；
- 可回溯來源的 `required_facts`；
- 不得出現在稿內的 `prohibited_values`；canonical JSON 只輸出其 SHA-256 與字數，
  不把未確認值交給口語稿作者；
- 只處理關鍵資料的 `pronunciation_entries`；
- 所有缺值、未確認值、未知分類與未知專名的 `review_items`。

核心事實類別為：小費、出團人數、不可脫隊、巴士行車時間、保險、護照效期、
房型、素食、電壓及固定天氣提醒。行程變更、座位、安全、個人用藥、簽證、
行動不便、單人房差等已知分類若有資料，也會成為來源綁定事實。
`group_notes` 是保存完整網頁證據的總括容器，不直接進旁白；旁白使用從中解析、
仍綁定同一來源的具體 notice，避免同一條款重複朗讀。

每個來源事實的 `protected_text` 是不可改變意思的最小口語子句。作者可以改標點、
空白及段落銜接，但不得以同義改寫取代這些子句；這項刻意保守的限制，讓本機規則
可以確定保護金額、人數、額度、期限、限制與責任範圍，而不是假裝能用關鍵字理解
任意中文語意。

缺少核心事實、沒有可用天氣、OP 欄位未確認、notice 分類未知或專名不在發音表時，
必須保留 `review_items`，但不阻止 source-bound 本機 DRAFT；缺少或未確認的值不得進入
旁白。草稿為 `BLOCKED`、來源衝突未解、事實沒有可追溯來源或來源完整性失敗時，
`ready` 才必須為 false。模型只能保留缺漏並請 OP review，不得自行補值。

## 固定段落與 marker

TXT 草稿依下列順序各出現一次 exact marker：

1. `<!-- section:product_date -->`
2. `<!-- section:tips_and_group_rules -->`
3. `<!-- section:transport -->`
4. `<!-- section:insurance_and_safety -->`
5. `<!-- section:passport_and_accessibility -->`
6. `<!-- section:diet_and_rooms -->`
7. `<!-- section:voltage_and_weather -->`
8. `<!-- section:closing -->`

Marker 是驗證控制資料，不交給 TTS。`narration_text_for_tts()` 只移除 exact marker，
不修改事實內容。

## 內容檢查

`check_script(narration_input, script)` 必須：

- 要求八個 marker 完整、唯一且順序正確；
- 在指定段落找到每個 `protected_text`；
- 逐一找到來源事實中的所有關鍵日期、金額、人數、時數、效期、百分比與電壓；
- 阻擋 narration input 未核准的新關鍵數字；
- 阻擋未解衝突、落選衝突值及未確認 OP 值；
- 阻擋已知的相反語意，例如把「不可脫隊」改成「可以脫隊」；
- 只在報告輸出 issue code、段落／fact ID、計數與雜湊，不回吐整份私有講稿。

字數估計以已通過的 Yating 短樣本基準 `3.6` 個可發音字元／秒計算，只供合成前
提示。估計過短或過長是 warning；6 至 8 分鐘是否通過，仍以合成後 WAV 的實際
frame 時間為唯一依據。

## 實際音訊時長

`validate_audio_duration()` 的接受範圍包含端點：`360.000` 至 `480.000` 秒。

- 第一次過短：只允許一次 `supplement_once`，補充 narration input 已提供的非關鍵
  說明，不得新增來源或事實。
- 第一次過長：只允許一次 `compress_once`，刪除重複與純銜接文字，不得刪改
  protected facts 或 critical values。
- 修訂一次後仍超界：`blocked` 並轉人工 review，不再自動改稿，也不靠加速語音
  掩蓋長度問題。

## 發音與自然度

發音表只自動處理可測試的關鍵資料：航空班號、機場代碼、日期、金額、`100V`
類電壓，以及大阪／關西、東北、北海道三區域的常見日文地名。未知地名或專名原樣
保留並進入 `UNKNOWN_PRONUNCIATION_TERM` review，不任意改字。

一般中文字詞偶發但仍可立即理解的音調不自然，不建立逐字例外、文案補丁或局部
SSML 音高調整。聽不清、可能改變語意或誤認姓名、地名、集合資訊、日期、班號、
機場代碼、金額與安全指示時才阻擋；同類問題跨句、跨去識別樣本重現時，才以固定
測試稿評估整體韻律或引擎。
