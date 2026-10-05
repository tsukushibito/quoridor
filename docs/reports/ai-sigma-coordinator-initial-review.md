# Sigma初期調査の評価と次実験

Beads issue / 実験ID / 試行 / 契約版 / 報告元スレッド:
quoridor-4lc / SIGMA-INITIAL-REVIEW / 1 / 目標契約1 / coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。
入力: SIGMA-HYP-INITIAL（子.2）とSIGMA-INFRA-INITIAL（子.3）。

判別した問い / 仮説:
現B0の計算支配箇所と固定Sigmaへの比較成立条件。BFS/確保、policy/value不足、将来NN推論、探索配分、無壁solverの5仮説を保持。いずれも改善の実測はない。最小の基準/内訳計測と独立した方法レビューを次に選ぶ。

実施内容 / コード・差分・環境・入力の参照:
hypothesis報告全文を読み、ローカルhash 8b4938e6bd1774a5313f808f8c5c0de3a67618c00cc63a4cd6efd404fde9a032を照合。steward報告受信全文とローカルhash 52b8d53b07cf725f1b53510048abfd0c4d4d13b03461f0c814e16695cb4ff5a5を照合。基準HEAD/移入hashはlaunch.json、lock/環境/実入力manifestは両報告を保持。

観測結果と数値 / ログ・raw resultへの参照:
統括が研究worktreeのapps/web/package.jsonをcreateRequireの起点に@quoridor/engine-bridgeをresolveし、realpathが /workspaces/quoridor/packages/engine-bridge/src/index.ts へ流れることを独立再現。追加準備なしの隔離実行仮説は不支持。steward可否判断を受入れ、担当本人のcloseは次の担当turnで実行する。初期hypothesisは反証案/再現根拠として受領し、重大条件の独立照合をcritic .4へ渡す。
quoridor-4lc.4 criticと.5 experimentに実際にsend、両方turn/start accepted=true。実受領thread/turn/契約hashは .artifacts/ai-sigma/dispatch/initial-reports-next.json。

支持する結論 / 支持しない結論 / 交絡要因と未確認:
現在のNode依存隔離問題を支持。B0/Sigmaの規約・encoding・thread/参照経路の差はhypothesisの読取報告であり、criticが一次コードで独立照合する。SigmaモデルSHA256/graph/provenance、実時間adapter/単一thread強制、非劣性基準は未確定。H1優先は安価な判別費用による配分であり、H1を真と採択していない。

実装失敗・実験不成立・negative resultの区別:
隔離仮説の不支持は基盤の観測。性能negative result/棋力改善/到達の結果はまだない。通信は成功。

再現コマンド / 独立再実行の状況:
timeout 15s node --input-type=moduleでcreateRequire(process.cwd()+'/apps/web/package.json')、realpathSync(req.resolve('@quoridor/engine-bridge'))。前報告の重い検証/性能計測は統括が実行していない。独立方法レビューはcritic .4へ実依頼済み。

書き込み停止 / 実行中プロセス・資源の残存:
hypothesis/stewardの書込み停止・自己処理終了報告とApp Server idleを確認して枠を解放。次は統括+critic+experimentの最大3役。実コードの唯一のwriterはexperiment、統括は契約/判断報告/受領記録のみ。ジョブPID/log/timeout/終了はexperiment契約で必須、正式計測と準備の競合は禁止。

保持する証拠 / 整理できる生成物:
初期2報告、固定参照commit/URL/hash、steward容量・機材観測、開始JSON、今回二契約と配送受領を保持。削除なし。実験が原B0 snapshot/未計測binaryを変更前に保存する。

次の提案 / 必要な判断:
報告待ちはcritic .4（比較規約/事前判定/H1方法）とexperiment .5（隔離/B0基準/排他内訳、可能ならbrowser診断）、報告先coordinator、通信目標quoridor-4lc。結果で一要因の高速化またはPV/推論/探索/solverへ配分を更新、成功候補は独立再実行。持ち時間・規約・モデル/参照版・開始局面・統計基準は勝敗前に固定。目標未達のためcloseしない。

予算:
全体締切UTC2026-10-01T01:17:58.145139+00:00/JST10:17:58、17:44UTC頃の残枠約7時間34分。初期両役正式計算/対戦/学習0、保存報告計83076bytes。開始17:17の厳密容量は未観測、steward17:24のworktree33099776bytes/launch438272bytes等を保守reserve基準として使用。
今回critic30分/1CPU/1GiB/32MiB/GPU0、experiment70分/準備2CPU・測定1CPU/4GiB/GPU0/新規合計4GiB以内。全体同時計算最大3CPU/5GiBで上限4CPU/8GiB以内。12GiBの新規保存枠から今回4GiBを予約し、残り8GiBから起動/文書/副次cache増分を差し引く。正確な新規残量・短い読取CPU累積は未確定で、experimentが準備前後の増分を記録。学習GPU累積0、今回は許可しない。正式比較窓では重い自チームジョブを停止し他者負荷は記録する。
