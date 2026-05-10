"""
XAU/USD EMA21/55クロス戦略 バックテスト
期間：2025年1月1日〜2026年5月10日
時間足：H1

実行方法：
  pip install yfinance pandas numpy matplotlib
  python3 xauusd_backtest.py

Claude Codeでそのまま使用可能。
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────
# 1. データ取得
# ─────────────────────────────────────────
print("XAU/USD H1データ取得中（2025年1月〜2026年5月）...")

# GC=F は金先物（最も流動性が高いCMEのゴールド先物）
# XAU/USDの現物に近い値動きをする
ticker = "GC=F"
df = yf.download(
    ticker,
    start="2025-01-01",
    end="2026-05-10",
    interval="1h",
    progress=False,
    auto_adjust=True
)

# カラム名を整理
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[0] for c in df.columns]
df = df[['Open', 'High', 'Low', 'Close']].dropna()

if df.empty:
    print("ERROR: データが取得できませんでした。")
    print("対処法：interval を '60m' に変更するか、別のtickerを試してください。")
    print("代替ticker：XAUUSD=X（現物に近い）")
    exit(1)

print(f"取得完了：{len(df)}本 / {df.index[0].date()} 〜 {df.index[-1].date()}")

# ─────────────────────────────────────────
# 2. テクニカル指標の計算
# ─────────────────────────────────────────

# EMA21 / EMA55（終値ベース）
df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
df['EMA55'] = df['Close'].ewm(span=55, adjust=False).mean()

# RSI(14)
delta = df['Close'].diff()
gain  = delta.clip(lower=0).rolling(14).mean()
loss  = (-delta.clip(upper=0)).rolling(14).mean()
rs    = gain / loss.replace(0, np.nan)
df['RSI'] = 100 - (100 / (1 + rs))

# ATR(14)
hl = df['High'] - df['Low']
hc = (df['High'] - df['Close'].shift()).abs()
lc = (df['Low']  - df['Close'].shift()).abs()
df['ATR'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()

# EMAクロスシグナル
df['EMA_above'] = (df['EMA21'] > df['EMA55']).astype(int)
df['Cross']     = df['EMA_above'].diff()
# Cross = +1：ゴールデンクロス（EMA21が55を上抜け）→ロング
# Cross = -1：デッドクロス（EMA21が55を下抜け）→ショート

# ─────────────────────────────────────────
# 3. エントリーフィルターの設定
# ─────────────────────────────────────────

# 時間フィルター：21:30〜23:30 JST = 12:30〜14:30 UTC
df.index = pd.to_datetime(df.index, utc=True)
hour_utc      = df.index.hour + df.index.minute / 60
df['in_session'] = (hour_utc >= 12.5) & (hour_utc <= 14.5)

# ATRフィルター：ATR(14) >= $8（H1の値動きが十分ある日のみ）
ATR_THRESHOLD = 8.0
df['atr_ok'] = df['ATR'] >= ATR_THRESHOLD

# RSIフィルター
#   ロング：40〜65（過買われ状態でのクロスを除外）
#   ショート：35〜60（過売られ状態でのクロスを除外）
df['rsi_long_ok']  = (df['RSI'] >= 40) & (df['RSI'] <= 65)
df['rsi_short_ok'] = (df['RSI'] >= 35) & (df['RSI'] <= 60)

df = df.dropna()

# ─────────────────────────────────────────
# 4. バックテストエンジン
# ─────────────────────────────────────────
SL_DOLLAR = 10.0   # 損切り：エントリー価格からの距離 $10
RR_RATIO  = 2.0    # R:R比率（利確 = 損切りの2倍 = $20）
TP_DOLLAR = SL_DOLLAR * RR_RATIO

trades    = []
in_trade  = False
direction = None
entry_price = sl_price = tp_price = entry_time = None

for i in range(1, len(df)):
    row = df.iloc[i]

    # ─── 保有中ポジションの管理 ───
    if in_trade:
        hit_sl = (direction == 'long'  and row['Low']  <= sl_price) or \
                 (direction == 'short' and row['High'] >= sl_price)
        hit_tp = (direction == 'long'  and row['High'] >= tp_price) or \
                 (direction == 'short' and row['Low']  <= tp_price)

        if hit_sl or hit_tp:
            exit_price = tp_price if hit_tp else sl_price
            pnl = (exit_price - entry_price) if direction == 'long' \
                  else (entry_price - exit_price)
            trades.append({
                'entry_time'  : entry_time,
                'exit_time'   : df.index[i],
                'direction'   : direction,
                'entry_price' : round(entry_price, 2),
                'exit_price'  : round(exit_price, 2),
                'sl'          : round(sl_price, 2),
                'tp'          : round(tp_price, 2),
                'pnl_usd'     : round(pnl, 2),
                'result'      : 'WIN' if hit_tp else 'LOSS',
                'rsi_at_entry': round(df.iloc[i-1]['RSI'], 1),
                'atr_at_entry': round(df.iloc[i-1]['ATR'], 2),
            })
            in_trade = False
        continue

    # ─── 新規エントリー判定 ───
    cross = row['Cross']
    if cross == 0:
        continue
    if not (row['in_session'] and row['atr_ok']):
        continue

    if cross > 0 and row['rsi_long_ok']:     # ゴールデンクロス → ロング
        direction   = 'long'
        entry_price = float(row['Close'])
        sl_price    = float(row['EMA55']) - SL_DOLLAR
        tp_price    = entry_price + TP_DOLLAR
        entry_time  = df.index[i]
        in_trade    = True

    elif cross < 0 and row['rsi_short_ok']:  # デッドクロス → ショート
        direction   = 'short'
        entry_price = float(row['Close'])
        sl_price    = float(row['EMA55']) + SL_DOLLAR
        tp_price    = entry_price - TP_DOLLAR
        entry_time  = df.index[i]
        in_trade    = True

# ─────────────────────────────────────────
# 5. 結果集計・表示
# ─────────────────────────────────────────
if not trades:
    print("\nトレードが発生しませんでした。")
    print("フィルター条件（時間帯・ATR・RSI）を緩めるか、期間を広げてみてください。")
    exit()

result_df = pd.DataFrame(trades)
wins      = result_df[result_df['result'] == 'WIN']
losses    = result_df[result_df['result'] == 'LOSS']

total     = len(result_df)
win_count = len(wins)
loss_count= len(losses)
win_rate  = win_count / total * 100
total_pnl = result_df['pnl_usd'].sum()
avg_win   = wins['pnl_usd'].mean()   if win_count   else 0
avg_loss  = losses['pnl_usd'].mean() if loss_count  else 0
pf        = wins['pnl_usd'].sum() / abs(losses['pnl_usd'].sum()) \
            if loss_count and losses['pnl_usd'].sum() != 0 else float('inf')
max_loss  = result_df['pnl_usd'].min()
max_gain  = result_df['pnl_usd'].max()

# 累積損益（最大ドローダウン計算用）
result_df['cum_pnl']  = result_df['pnl_usd'].cumsum()
result_df['cum_max']  = result_df['cum_pnl'].cummax()
result_df['drawdown'] = result_df['cum_max'] - result_df['cum_pnl']
max_dd = result_df['drawdown'].max()

# 月別集計
result_df['month'] = result_df['entry_time'].dt.to_period('M')
monthly = result_df.groupby('month')['pnl_usd'].agg(
    total_pnl='sum', trades='count',
    wins=lambda x: (x > 0).sum()
).reset_index()

# 方向別集計
direction_summary = result_df.groupby('direction').agg(
    count=('pnl_usd','count'),
    wins=('result', lambda x: (x=='WIN').sum()),
    total_pnl=('pnl_usd','sum')
).reset_index()

# ─── 表示 ───
sep = "=" * 62
print("\n" + sep)
print("  EMA21/55クロス戦略　バックテスト結果")
print(f"  期間：2025年1月〜2026年5月　｜　XAU/USD H1")
print(f"  ブローカー想定：FXTF GX（ゼロスプレッド）")
print(f"  損切：${SL_DOLLAR}　利確：${TP_DOLLAR}　R:R=1:{RR_RATIO:.0f}")
print(sep)

print(f"\n【全体成績】")
print(f"  総トレード数        : {total:>4} 回")
print(f"  勝率                : {win_rate:>6.1f}%  （{win_count}勝 / {loss_count}敗）")
print(f"  総損益              : ${total_pnl:>+8.2f} / ロット")
print(f"  プロフィットファクター : {pf:>6.2f}  （1.0超が目標、1.3以上が優秀）")
print(f"  平均利益            : ${avg_win:>+7.2f}")
print(f"  平均損失            : ${avg_loss:>+7.2f}")
print(f"  最大1回利益         : ${max_gain:>+7.2f}")
print(f"  最大1回損失         : ${max_loss:>+7.2f}")
print(f"  最大ドローダウン     : ${max_dd:>7.2f}")

print(f"\n【月別損益】")
print(f"  {'月':^8}  {'損益':>10}  {'回数':>4}  {'勝率':>6}  評価")
print(f"  {'-'*45}")
for _, r in monthly.iterrows():
    wr_m = r['wins'] / r['trades'] * 100 if r['trades'] > 0 else 0
    mark = "◎ 黒字" if r['total_pnl'] > 0 else "✕ 赤字"
    print(f"  {str(r['month']):^8}  ${r['total_pnl']:>+8.2f}  {int(r['trades']):>3}回  {wr_m:>5.1f}%  {mark}")

print(f"\n【方向別成績】")
for _, r in direction_summary.iterrows():
    wr_d = r['wins'] / r['count'] * 100 if r['count'] > 0 else 0
    print(f"  {r['direction'].upper():5}: {int(r['count'])}回 / 勝率{wr_d:.1f}% / 合計${r['total_pnl']:+.2f}")

print(f"\n【直近15トレード】")
print(f"  {'エントリー日時':^20} {'方向':^6} {'損益':>9} {'結果':^5}")
print(f"  {'-'*48}")
for _, t in result_df.tail(15).iterrows():
    print(f"  {str(t['entry_time'])[:16]:^20} {t['direction']:^6} ${t['pnl_usd']:>+7.2f} {t['result']:^5}")

print(f"\n【判定】")
if pf >= 1.3 and win_rate >= 45:
    print("  ✓ プロフィットファクター1.3以上 + 勝率45%以上 → デモ口座で検証を継続する価値あり")
elif pf >= 1.0:
    print("  △ プロフィットファクター1.0〜1.3 → 手法の改良（フィルター追加等）が必要")
else:
    print("  ✕ プロフィットファクター1.0未満 → この条件ではリアル口座での使用は危険")

print(f"\n注意事項：")
print(f"  ・本結果はCME金先物（GC=F）の過去データによるバックテストです")
print(f"  ・スプレッド・スリッページ・手数料（FXTF GXの建玉連動手数料）は未考慮")
print(f"  ・FXTF GXの実際のスプレッドを加味すると成績は変動します")
print(f"  ・過去の成績は将来の利益を保証しません")
print(sep + "\n")

# CSV保存
result_df.to_csv("backtest_xauusd_ema_2025.csv", index=False)
print("詳細データを保存: backtest_xauusd_ema_2025.csv")

# ─────────────────────────────────────────
# 6. （任意）チャート描画
# ─────────────────────────────────────────
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)

    # 累積損益チャート
    ax1 = axes[0]
    ax1.plot(result_df['entry_time'], result_df['cum_pnl'],
             color='steelblue', linewidth=1.5, label='累積損益')
    ax1.axhline(y=0, color='gray', linewidth=0.5, linestyle='--')
    ax1.fill_between(result_df['entry_time'], result_df['cum_pnl'],
                     alpha=0.1, color='steelblue')
    ax1.set_title('EMA21/55 XAU/USD 累積損益（$/ロット）', fontsize=12)
    ax1.set_ylabel('累積損益 ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 月別棒グラフ
    ax2 = axes[1]
    colors = ['steelblue' if v > 0 else 'tomato' for v in monthly['total_pnl']]
    ax2.bar(monthly['month'].astype(str), monthly['total_pnl'], color=colors)
    ax2.axhline(y=0, color='gray', linewidth=0.5)
    ax2.set_title('月別損益', fontsize=12)
    ax2.set_ylabel('損益 ($)')
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(True, alpha=0.3, axis='y')

    # 勝率推移（20トレード移動平均）
    ax3 = axes[2]
    result_df['win_flag'] = (result_df['result'] == 'WIN').astype(int)
    if len(result_df) >= 20:
        rolling_wr = result_df['win_flag'].rolling(20).mean() * 100
        ax3.plot(result_df['entry_time'], rolling_wr,
                 color='darkorange', linewidth=1.5, label='勝率（20回移動平均）')
        ax3.axhline(y=50, color='gray', linewidth=0.5, linestyle='--', label='50%ライン')
        ax3.set_title('勝率推移（直近20トレード移動平均）', fontsize=12)
        ax3.set_ylabel('勝率 (%)')
        ax3.set_ylim(0, 100)
        ax3.legend()
        ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('backtest_result_chart.png', dpi=150, bbox_inches='tight')
    print("チャートを保存: backtest_result_chart.png")
    plt.close()
except ImportError:
    print("（matplotlibがない場合はチャートは省略されます）")
except Exception as e:
    print(f"（チャート描画エラー: {e}）")
