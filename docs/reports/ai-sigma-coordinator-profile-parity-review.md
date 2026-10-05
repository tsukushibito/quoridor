# B0計測・参照fixtureの評価と一要因試作

Beads issue / 実験ID / 試行 / 契約版 / 報告元スレッド:
quoridor-4lc / SIGMA-PROFILE-PARITY-REVIEW / 1 / 目標契約1 / coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。受信SIGMA-B0-PROFILE(.5)、SIGMA-PARITY-PLAN(.6)。

判別した問い / 仮説:
Legal/BFSが支配するという実測報告を独立再現でき、queueだけの試作へ費用を配分するか。参照側の規約/特徴/Action goldenを後続Rust parityに使用可能か。

実施内容 / コード・差分・環境・入力の参照:
.5報告hash be856e7727e129931d46bf0a8bef9dff836608583bde9a8d016994261329b044、.6報告hash3f2a7ccce82552bca670b3e518fda84953f15421623504ceef9d34a9d6143460、fixture hash206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffbを照合。原source/lock/binary/fixture正本は .artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/ のimmutable manifest。launch.jsonとHEAD1482df8…は継承、現在sourceだけで原B0を特定しない。

観測結果と数値 / ログ・raw resultへの参照:
.5raw/資源/終了recordを限定読取。reported coarse R_exp98.00–99.09%/R_all96.82–98.53%、全6caseの元run median gate<=5%。full detailed clock gate超過、allocation未測定、全検索Wasmwall未取得、広いUI timeout未解決を保持。
統括が固定original/coarse immutable binaryをCPU2で短い別2round再実行。全6caseで合法順/距離/全transition/selected/rootbits/statsの厳密一致とglobal/Expand exclusive和をassert。R_exp sample最小97.57%以上を再現。原bin6warm/coarse20warmの不均等な短いsampleで各case median overheadはinitial4.02%、opening3.29%、walled-midgame5.13%、p2 2.32%、jump2.87%、many-walls0.41%。wallcaseは事前5%gateを僅かに超え、全面受入れ保留。より有利なsampleへの再試行はしていない。独立raw/PID/exit/hashは .artifacts/ai-sigma/verification/PROFILE-COORD-1/{rerun.py,summary.json,*.jsonl}。
.6は28fixture/合法replay20・synthetic8、出所text/モデルmetadataを提出。Rust/NN/parity完了ではない。getLegalActionsとisActionLegalの反復差、終局raw maskとeffective terminal、synthetic counts/plyを区別する条件を保持。
次を実送信: experiment .7のqueue-only試作（60分、native/Wasm別比較、出力一致と独立受入れまで候補）、critic .8の.5最終snapshot/raw再集計と.6自己copy再生成（20分）。両accepted=true、実受領thread/turnは .artifacts/ai-sigma/dispatch/profile-parity-reports-next.json。

支持する結論 / 支持しない結論 / 交絡要因と未確認:
探索的native窓で高いLegal/BFS占有率と出力同一性を独立確認。これは同PCSigma棋力差の原因やqueuegainを証明しない。wallcase overgateと少ない原sampleは計測器の頑健性未確認として残し、.8で再評価。.5全gate通過と独立再現の1case超過を混ぜない。native速度をWasmへ換算しない。模型provenance完全性/配布、実model SHA/graph/数値、Rust規約/history/deadline、同時間対局、棋力到達は未実施。

実装失敗・実験不成立・negative resultの区別:
full時計/独立wallcase gate不成立は測定妥当性の限界。H1不支持やqueue最適化失敗ではない。広いUI試験timeoutは原因未特定、performance単独成功では解消しない。元実装/補助fixtureの失敗証拠は保持。今回最適化成果はまだなく、未達のまま継続。

再現コマンド / 独立再実行の状況:
timeout120s taskset -c2 python3 -B .artifacts/ai-sigma/verification/PROFILE-COORD-1/rerun.py、exit0/約3.44秒。再生成scriptは自己verification出力だけを書き、.5raw/summaryを上書きしていない。再実行したbinaryはshaを各jobに記録。計算配分CPU1/256MiB/32MiB/120秒で、全child回収済み。critic .8は生データ再集計/短いNode自己copyのみ、並行.7と重い測定/buildを競合させない。

書き込み停止 / 実行中プロセス・資源の残存:
.5自己child終了/port5183解放、.6fetch/Node終了と両担当idleを確認。.7experimentと.8criticだけ起動し統括込み3役。唯一のcodewriterはexperiment。統括の短いverification processは終了、source/製品UI/描画変更なし。各ownerはdeadline/guard/stop/exitと書込み停止を報告する。

保持する証拠 / 整理できる生成物:
原B0/.5source/lock/binary/全raw/旧clock失敗/終了、.6原文/notice/generator/inputs/schema/fixture/classification、統括short raw、今回契約/実受領を保持。削除・共有環境更新なし。使用済みbaselineをcandidateで上書きしない。

次の提案 / 必要な判断:
報告待ちはexperiment .7の同一性/native-Wasm queue候補、critic .8の器/fixture限定受入れ。最終raw受入れ後.5/.6の担当本人closeを指示し、.7candidateは独立再実行を経て採否。モデル取得/graph/parity・研究rule context/deadline実装は次の競合枝として残す。正式対戦は事前protocolのgate通過までno-go。

予算:
全体締切UTC2026-10-01T01:17:58.145139+00:00/JST10:17:58、18:55頃残り約6時間23分。.5実新規約520396800bytes（0.485GiB）、RSS観測約1.559GiB、.6約1706684bytes。初期worktree/launch/文書等reserveを含め既存消費は保守約0.55GiB、厳密全体はowner集計待ち。.5未使用予約は解放。.7追加1GiB/所有全体2GiB上限・RAM4GiB/準備2CPU測定1CPU/GPU0、.8 64MiB/1GiB/CPU0に1CPU/GPU0。全体4CPU/8GiB/12GiB、今回最大3CPU/5GiB以内。GPU/学習/正式対局0。速度・到達未確認。
