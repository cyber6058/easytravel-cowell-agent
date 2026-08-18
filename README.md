# EasyTravel Cowell Agent

立益旅行社專用的本機工具。本專案包含 Cowell 名單／分房與獨立的說明會資料
產生器；兩者套件、設定與權限互不相依。

Cowell Skill 處理兩條工作流：

1. 從護照 PDF／照片整理、驗證並輸出科威官方 19 欄 Excel 名單。
2. 針對 OP 已建立的科威訂單，讀取 DOCX／XLSX 分房表後：
   - 系統內完全沒有相符姓名：一次匯入完整名單，再填入分房；
   - 系統內所有姓名都已相符：只填入分房；
   - 只有部分姓名相符：停止，不做部分寫入，交由 OP 修正後重跑。

本專案不建立團體或訂單，也不包含付款、機位、報表等其他 Cowell CLI
功能。所有艙等都可使用；若訂單有多個可用艙等，由 OP 提供旅客序號到
艙等的對照。成人／小孩／嬰兒不阻擋作業，程式保留科威原值並顯示警告。

## 安全模型

- rooms parse、rooms plan 完全離線。
- rooms preview 只讀取科威並產生精確確認字串。
- rooms apply 必須帶入最後一次 plan 的確認字串，且執行前需取得當次
  OP 核准；寫入後會重新讀取並核對姓名與分房。
- 護照、分房表、旅客 JSON、輸出 Excel、登入狀態都只留在本機，不得
  commit 或上傳 GitHub。

## 開發環境

需求：Windows、Python 3.12+、Google Chrome。

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m cowell_cli.cli --help
~~~

離線可完整測試解析、名單驗證、規劃、安全規則與模擬科威頁面。沒有科威
帳號仍無法驗證真實頁面結構與正式寫入；到立益公司後應先跑離線測試，再
登入受控 Chrome，只執行 auth status 與 rooms preview。正式
rooms apply 是下一個獨立核准關卡。

## 安裝給 Agent

可直接 clone 本 repo 開發，或建立安裝包：

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_easytravel_cowell_package.ps1
~~~

安裝包內含單一 easytravel-cowell-cli Skill。詳細操作與安全限制位於
[SKILL.md](packaging/easytravel-cowell-cli/plugins/easytravel-cowell-cli/skills/easytravel-cowell-cli/SKILL.md)。

## 到公司電腦驗收

~~~powershell
git clone https://github.com/cyber6058/easytravel-cowell-agent.git
cd easytravel-cowell-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
~~~

先確認測試綠燈，再依 Skill 安裝說明設定 Cowell URL 與受控 Chrome。
不要把真實護照、分房表或產出檔放在 repo 內。

## 說明會資料 Skill

`easytravel-briefing-materials` 針對單一新魅力大阪、東北或北海道產品，從 URL、
本機行程 PDF 或兩者建立可審核 manifest，再依序產生 LIST Word 草稿、逐字稿、
Microsoft Yating 本機語音與字幕。缺值、來源衝突、範本漂移或 QA 失敗都會保留為
review，不猜值、不使用雲端 TTS，也不自動傳 LINE。

0.2.1 使用既有 0.2.0 校準；使用者在同一則要求提供新魅力 URL／PDF 並要求產生說明會資料，
即可授權 one local DRAFT：系統使用唯一 canonical LIST master，依來源實際天數動態
建列並安全續頁，接著完成逐頁 QA 與 Yating 語音。校準、CONFIRMED、LINE、上傳、
部署與 Cowell 仍各自需要獨立授權。

建立獨立 `0.2.1` 安裝包：

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_easytravel_briefing_package.ps1
~~~

安裝包只含 `travel_briefing`、briefing scripts／config、Codex plugin 與由同一份
canonical 規則產生的 Claude Skill，不含 Cowell、私有 LIST 範本、來源或產出。
操作邊界見
[SKILL.md](packaging/easytravel-briefing-materials/shared/SKILL.md)。
