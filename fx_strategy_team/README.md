# FX勝ち戦略チーム — GBPJPY / GBPUSD

「FXで勝てる戦略を考えるチーム」として、ファンダメンタルズ担当・テクニカル担当・リスク管理担当の3名（Claude のサブエージェント）が調査した内容を、統合役が1つの売買ルールセットにまとめたプロジェクトです。対象はGBPJPY（ポンド/円）を主軸、GBPUSD（ポンド/ドル）を副軸としています。

**このREADMEに書かれている数値・事実にはすべて出典URLを付けています。出典のない断定は書いていません。** 該当調査は2026年9月6日時点でWeb検索を行った結果であり、相場・金利は日々変わるため、実際にトレードする前には必ず最新情報を再確認してください。

---

## 目次

1. [チーム体制](#チーム体制)
2. [担当A: ファンダメンタルズ分析](#担当a-ファンダメンタルズ分析)
3. [担当B: テクニカル分析](#担当b-テクニカル分析)
4. [担当C: リスク管理](#担当c-リスク管理)
5. [統合戦略: 具体的な売買ルール](#統合戦略-具体的な売買ルール)
6. [なぜGBPJPYを主軸にするか](#なぜgbpjpyを主軸にするか)
7. [セットアップ手順](#セットアップ手順)
8. [使い方](#使い方)
9. [ファイル構成](#ファイル構成)
10. [限界・免責事項](#限界免責事項)

---

## チーム体制

| 担当 | 役割 |
|------|------|
| 担当A: ファンダメンタルズ分析 | BOE/BOJ/FRBの金利政策、金利差とキャリートレードの関係を調査 |
| 担当B: テクニカル分析 | GBPJPY/GBPUSDのトレンド特性、ブレイクアウト手法・トレンドフィルターを調査 |
| 担当C: リスク管理 | ポジションサイジング、ポートフォリオ全体のリスク上限、ドローダウン管理を調査 |
| 統合役 | 3名の調査結果を突き合わせ、実装可能な売買ルールとコードにまとめる |

---

## 担当A: ファンダメンタルズ分析

- **BOE(イングランド銀行)政策金利: 3.75%**。2026年7月30日のMPC(金融政策委員会)で据え置き決定(9名中6対3、反対派3名は利上げを主張)。次回会合は2026年9月17日。英CPIは8月時点で3.8%まで加速(中東情勢による原油高が要因)。
  出典: [Bank of England 金融政策サマリー](https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/september-2026), [Private Finance](https://www.privatefinance.co.uk/base-rate-held-july-2026/)
- **BOJ(日本銀行)政策金利: 1.00%**。2026年6月16日の会合で0.75%→1.00%に利上げ(1995年以来の水準)。次回会合は2026年9月17-18日で、追加利上げの観測も報じられている。
  出典: [日本銀行 公式発表(PDF)](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260616a.pdf), [CNBC](https://www.cnbc.com/2026/06/16/boj-rate-hike-historic-inflation.html)
- **FRB FF金利誘導目標: 3.50〜3.75%**。2026年7月29日のFOMCで据え置き(9対3)。次回会合は2026年9月15-16日。
  出典: [FRB公式発表](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm)
- **金利差**: GBP-JPY間は約+2.75ポイント(GBP優位)、GBP-USD間は約±0.1ポイント(ほぼ拮抗)。金利が高い通貨を買い低い通貨を売る「キャリートレード」の考え方に基づけば、GBPJPYの方が金利差による方向性の根拠が明確。
  出典(キャリートレードの一般的説明): [fxsignalsai.com](https://fxsignalsai.com/blog/the-carry-trade-explained-profiting-from-interest-rate-differentials)
- **リスク要因**: BOJのタカ派転換により円キャリートレードの「巻き戻し(アンワインド)」が市場のテーマとして再浮上している。2026年9月15-18日にFOMC・BOE・BOJの決定が連続するため、この期間はボラティリティ急変に警戒が必要。
  出典: [moomoo.com](https://www.moomoo.com/community/feed/has-the-yen-carry-trade-entered-a-turning-point-in-116456627437574)

## 担当B: テクニカル分析

- **GBPJPY**: 週足は209.55を起点とした上昇トレンドが継続中で、週足55EMA(約209.68)を上抜けた状態を維持。月足でも2011年安値(116.83)からの長期上昇トレンドが進行中。RSIは56付近で中立〜やや強気。
  出典: [ActionForex](https://www.actionforex.com/technical-outlook/gbpjpy-outlook/652255-gbp-jpy-weekly-outlook-468/), [TIOMarkets](https://tiomarkets.com/article/gbp-jpy-market-analysis-price-forecast-support-resistance-2026-09-03), [Investing.com](https://www.investing.com/currencies/gbp-jpy-technical)
- **GBPUSD**: 1.3425〜1.37のレンジ内で推移し、移動平均線群が収束、RSIも50近辺で中立。方向感に乏しくレンジ相場的な値動き。
  出典: [DailyForex](https://www.dailyforex.com/forex-technical-analysis/2026/09/gbpusd-price-outlook-usd-strength-gbp-pressure-3-september-2026/249294), [TIOMarkets](https://tiomarkets.com/article/gbp-usd-market-analysis-price-forecast-september-2026-09-01)
- **採用手法: ドンチャンチャネル・ブレイクアウト(タートルズSystem1)**。過去20日高値を上抜けたら買い、安値を割ったら売り。手仕舞いは10日安値割れ(ロング)/10日高値超え(ショート)。
  出典: [The Turtle Trader](https://www.theturtletrader.com/turtle-trading-rules/), [Deepvue](https://deepvue.com/indicators/donchian-channels-the-breakout-traders/)
- **EMAトレンドフィルター**: 短期EMAが長期EMAより上にある間のみ買いシグナルを採用(逆も同様)。ダマシを減らす目的で広く使われる。
  出典: [LuxAlgo](https://www.luxalgo.com/blog/2-moving-average-crossover-strategies-explained/), [TrendSpider](https://trendspider.com/learning-center/moving-average-crossover-strategies/)
- **ATR(Average True Range)**: J.ウェルズ・ワイルダー考案のボラティリティ指標。損切り幅を「直近価格からATRの1.5〜4倍」に設定する手法が一般的。
  出典: [IG](https://www.ig.com/en/trading-strategies/what-is-the-average-true-range--atr--indicator-and-how-do-you-tr-240905), [LuxAlgo](https://www.luxalgo.com/blog/average-true-range-dynamic-stop-loss-levels/)

## 担当C: リスク管理

- **1トレードあたりのリスク: 口座資金の1〜2%まで**が業界で広く使われる基準(固定比率法)。
  出典: [CME Group](https://www.cmegroup.com/education/courses/trade-and-risk-management/the-2-percent-rule), [Trade That Swing](https://tradethatswing.com/the-1-risk-rule-for-day-trading-and-swing-trading/)
- **ATRベースのポジションサイジング計算式**: `ポジションサイズ = (口座資金 × リスク%) ÷ (ATR × ストップ倍率)`。
  出典: [quantstock.org](https://quantstock.org/calculators/atr-position-size), [MQL5](https://www.mql5.com/en/blogs/post/774444)
- **ポートフォリオヒート(合計リスク上限)**: 複数ポジション保有時の合計リスクにも上限を設けるべきで、Alexander Elder氏の「6%ルール」(1トレード2%以内・合計6%以内)が広く引用される。
  出典: [TD Ameritrade](https://tickertape.tdameritrade.com/trading/rules-to-manage-risk-15908), [fxfoundations.com](https://fxfoundations.com/learn/risk-management/portfolio-heat)
- **ドローダウン管理**: 資金がピークから10〜20%減少したら段階的にリスクを縮小・停止する階層型ルールが一般的。
  出典: [tradingblitz.com](https://tradingblitz.com/learn/risk-management/drawdown-rules-for-traders-how-to-survive-losing-streaks/), [prop-trading.info](https://prop-trading.info/guides-and-tutorials/risk-management-tutorials/maximum-drawdown-strategy-for-traders/)
- **FX特有の注意点**: 高レバレッジによる証拠金不足リスク、週末の窓開け(ギャップ)、スワップポイント。英国(FCA)・EU(ESMA)は主要通貨ペアのレバレッジを30倍に制限し、ネガティブバランスプロテクションを義務付けている。
  出典: [FCA](https://www.fca.org.uk/news/statements/fca-statement-esma-temporary-product-intervention-retail-cfd-binary-options), [ESMA](https://www.esma.europa.eu/node/84933)

---

## 統合戦略: 具体的な売買ルール

担当A/B/Cの調査結果を踏まえ、統合役が以下のルールに固定しました。実装は `src/` 以下のPythonコードを参照してください。

### 1. トレンドフィルター
- 日足EMA50 > EMA200 → 上昇トレンド局面(ロングのみ検討)
- 日足EMA50 < EMA200 → 下降トレンド局面(ショートのみ検討)

### 2. エントリー
- 上昇トレンド中、終値が過去20日高値(当日を含まない)を上抜けたら **買い**
- 下降トレンド中、終値が過去20日安値を割り込んだら **売り**

### 3. 損切り・手仕舞い
- 損切り: エントリー価格 ± ATR(14)×3(GBPJPYの高いボラティリティを踏まえ、担当Bが調査した1.5〜4倍のレンジの上限寄りを採用)
- 通常の手仕舞い: ロングは過去10日安値割れ、ショートは過去10日高値超えで決済(タートルズSystem1の手仕舞いルール)

### 4. ポジションサイジング
- 1トレードのリスクはGBPJPYで口座資金の**0.75%**、GBPUSDで**1.0%**(担当CはGBPJPYの方がボラティリティ・窓開けリスクが大きいため保守的な数値を推奨)
- サイズ = (口座資金 × リスク%) ÷ (ATR × 3)

### 5. ポートフォリオ全体のリスク上限
- GBPJPY・GBPUSDを同時に保有する場合、合計リスクは口座資金の**6%以内**(Elder氏の6%ルールを採用。両ペアともGBP絡みで値動きが相関しやすい点に注意)

### 6. ドローダウン管理
- 資金がピークから**10%**減少 → 新規トレードのリスクを半分に縮小
- 資金がピークから**20%**減少 → 新規トレードを停止し、戦略全体を見直す

---

## なぜGBPJPYを主軸にするか

1. **金利差(担当A)**: GBP-JPY間の金利差(約2.75pt)はGBP-USD間(約0.1pt)より大きく、キャリートレードとしての方向性の根拠がある。ただしBOJの正常化で差は縮小傾向にあり、キャリー巻き戻しリスクも同時に存在する。
2. **トレンド構造(担当B)**: GBPJPYは週足・月足ともに明確な上昇トレンド構造にあるのに対し、GBPUSDはレンジ相場的でブレイクアウト戦略にとってダマシが発生しやすい地合いにある。
3. **リスク管理上の留意点(担当C)**: GBPJPYはボラティリティが高い分、ATRに基づく損切り幅も広くなり、ロット数は自動的に小さくなるよう設計している(リスク%もGBPUSDより低く設定)。

GBPUSDは金利差の根拠が薄いため、本戦略では副軸(レンジ相場向けの補助的な扱い)としており、主軸としての採用はGBPJPYとしています。

---

## セットアップ手順

```bash
cd fx_strategy_team
pip install -r requirements.txt
```

## 使い方

このツールは**ユーザー自身が用意した実際のヒストリカルCSVデータ**に対してバックテストを実行するためのものです。このリポジトリの実行環境からは為替データAPIへの直接アクセスができないため、実データは同梱していません(理由は「限界・免責事項」を参照)。

```bash
# 動作確認用(架空のサンプルデータ。実際の相場データではありません)
python src/main.py --data sample_data/gbpjpy_sample_FICTIONAL.csv --pair GBPJPY --sample

# 実データで実行する場合(date,open,high,low,close の列を持つCSVを用意)
python src/main.py --data /path/to/your_real_gbpjpy_daily.csv --pair GBPJPY
```

実行するとコンソールに勝率・プロフィットファクター・最大ドローダウン等のサマリーが表示され、`output/reports/` にExcelレポート(トレード一覧・資金推移グラフ付き)が生成されます。

実データを用意する方法の例:
- ブローカー(MT4/MT5)のヒストリカルデータをCSVエクスポート
- Alpha Vantage / OANDA 等のAPI(要ユーザー自身のAPIキー)から取得しCSV化
- `src/data_loader.py` の `load_from_csv()` が読み込める形式(`date,open,high,low,close`)に整形

---

## ファイル構成

```
fx_strategy_team/
├── README.md                    ← このファイル
├── requirements.txt
├── config/
│   └── settings.json             ← 通貨ペアごとの戦略パラメータ
├── src/
│   ├── main.py                   ← CLIエントリーポイント
│   ├── data_loader.py            ← CSV読み込み
│   ├── indicators.py             ← SMA/EMA/ATR/RSI/Donchianチャネル
│   ├── strategy.py               ← シグナル生成(トレンドフィルター+ブレイクアウト)
│   ├── risk_manager.py           ← ポジションサイジング/ポートフォリオヒート/ドローダウン管理
│   ├── backtester.py             ← バックテストエンジン
│   └── report_generator.py       ← Excelレポート生成
├── sample_data/
│   └── gbpjpy_sample_FICTIONAL.csv ← 動作確認専用の架空データ(実データではない)
└── output/reports/               ← 生成されたレポート(実行時に自動作成)
```

---

## 限界・免責事項

- **本ツールは実際の為替ヒストリカルデータを内蔵していません。** この実行環境からは為替データAPI(stooq, frankfurter.app等)への直接アクセスが利用ポリシー上ブロックされており、根拠のない数値を作り出さないという方針上、実データによる「本物の」バックテスト成績をこのプロジェクト内で提示することはできません。`sample_data/` の架空データはコードが正しく動作することを確認するためだけのものです。
- 上記のファンダメンタルズ・テクニカルの記述はすべて2026年9月6日時点のWeb検索結果に基づく出典付きの情報です。相場・金利情勢は日々変化するため、実際にトレードする前には必ず最新の情報を再確認してください。
- 本戦略は公開されている一般的なトレンドフォロー手法(タートルズSystem1、EMAトレンドフィルター、ATRベースのリスク管理)を組み合わせたものであり、将来の相場で利益を保証するものではありません。過去の実績・調査結果は将来の成果を保証しません。
- 実際の資金でのトレードは自己責任で行ってください。
