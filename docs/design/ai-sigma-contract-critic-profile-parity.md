# SIGMA-PROFILE-PARITY-CRITIC / 試行1 / 契約版1

目標quoridor-4lc、子issue quoridor-4lc.8。critic / 01a0f31d-8227-7e03-a7e6-915b4918c11b、coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94へ報告。
目標契約 docs/design/ai-sigma-research-goal.md版1とAGENTS/common/critic/team design/AI設計/storage policy/handoffを継承したユーザー自律権限内の検証依頼。追加subagent0。場所 /workspaces/quoridor/.worktree/ai-sigma / codex/ai-sigma。
開始ready、目標/自子/.4をshow、pauseなしなら自分の.8だけclaim。実装.5/.7や他担当.6/目標/.1はclaim/closeしない。
以前.4報告の開始17:45:48→停止18:16:14.649は30分26.649秒。『30分上限内』表記は不成立。旧報告hashは証拠として保持し上書きしない。docs/reports/ai-sigma-critic-time-correction.mdへ自分の時刻・停止/原因・予算遵守不成立を訂正し、.4notesへ参照・限定終了理由を追記して本人close。統括は方法内容を証拠として受領しているが、期限遵守/全面契約成功は認定していない。.4closeは研究成功/目標closeを意味しない。

今回唯一の書込み docs/reports/ai-sigma-critic-profile-parity.md、上記時間訂正、.artifacts/ai-sigma/verification/CRITIC-PROFILE-PARITY/ の自己copy/確認log/小script/summary。原.5/.6artifactやsource/共有docs/registry/envを変更しない。20分以内（最後3分を保存停止reportに確保）、1CPU affinity0/RAM1GiB/新規64MiB/GPU0。短いNode/Pythonのみ、native速度run/compile/正式性能測定/モデル取得/依存更新/対戦/学習0。
全体deadlineUTC2026-10-01T01:17:58.145139+00:00/JST10:17:58。18:52UTC頃残り約6時間26分。experiment .7は唯一のcodewriter、準備2CPU/測定CPU2/4GiB、所有保存上限2GiB（.5既存含む、今回追加1GiB）。hypothesis停止idle、あなたでLLM統括+experiment+critic最大3。計算最大3CPU/5GiB。新規全体12GiB、既存実験観測約0.485GiB＋初期reserve/文書＋.6約1.63MiBから次増分を計上。GPU/学習/正式対戦0。CPU0のtext/Node確認を測定の無競合根拠としない。

入力:
- docs/reports/ai-sigma-experiment-profile.md SHA256 be856e7727e129931d46bf0a8bef9dff836608583bde9a8d016994261329b044、.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/ のfinal-source（読取版正本、現在codeは.7で変わる）、final-source-hashes、comparison-contract2 raw/事前fixed method/旧失敗/元control bin、shutdown/resource。
- .artifacts/ai-sigma/verification/PROFILE-COORD-1/summary.jsonとrerun.py/raw（統括の短い独立2round）。元6warm/coarse20warm、全6case決定的出力とexclusive保存一致、全R_exp>=97.57%。walled-midgame overhead5.13%で5%gate超過、他5case0.41–4.02%。元.5の全gate通過とは条件・分散・標本数が違うのでgate頑健性/全面受入れは保留。
- docs/reports/ai-sigma-hypothesis-parity.md SHA256 3f2a7ccce82552bca670b3e518fda84953f15421623504ceef9d34a9d6143460、.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/（fixtures hash206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、28case/20legal/8synthetic、全manifest）。
- docs/design/ai-sigma-comparison-protocol.md（方式のみ、正式T/m/pool/adapterは未凍結）、launch.json/初期2報告/自.4。

問い1/反証/検証:
最終coarse器はExpand祖先を直接持ちLegal内DistanceはLegalに含めてunionを低overheadで測れるか。最終snapshotのコードとrawを独立読取し、metrics_in_expandの祖先、nestedexclusive、coarseの未計測counts、cap fallback Expand外分類を確認。全rawの合法順/距離/遷移/root action/prior/visits/value bits/stats同一性、exclusive和、R_exp/R_all/f_expandの再計算、各case gate、originalとoffの対照条件/順序/sample数を自scriptで再集計して報告。既存analyze-contract2.pyは原native-summaryを書き換えるので原pathで実行しない。別outputへ独立算術を保存。
低歪み主分類のgateを勝手に緩めない。統括short replayのwallcase超過を選別して削除しない。98%からqueuegainへ飛躍しない。5%未達時の結論はそのrun計測妥当性保留、H1不支持/最適化失敗と混ぜない。allocationは未測定のまま、full詳細時計超過は参考値。Wasm全探索wall未測定と広いUI timeoutの未特定原因を維持。最終受入れを全面可・限定可・追加検証必要に分ける。今回の検証は重い速度再測定をしないので超過率の精密値を確定しない。

問い2/反証/検証:
参照fixtureは固定raw JSから再生成でき、合法20/人工8を区別してRust規約/特徴変換へ渡せるか。manifest全payloadhash/schema/classificationを照合し、source/getLegalActionsとisActionLegalの反復差、terminal raw legal集合とeffective terminalの区別、goal at200の優先、P2/HVsegment/136↔209の写像/assertが適切かを批判。
自己copy範囲へ必要なgenerator/source/inputをコピーして再生成。reexecute.pyとgenerate.mjsは原fixtures/logを書き換えるので**原directoryで実行しない**。コードのpathを先に読んでコピー側へ出力できることを確認、output pathだけの最小adapterが必要ならpatch/hashを記録。元inputs/source/generatorと同bytesの期待fixture hashを得られるかを独立役として検証する。元artifactの試験前後hash不変を確認。Rust/NN内部展開は今回実行しない、参照側の一致をRust parity完了とはしない。
synthetic counts/ply199 count0/終端raw mask等は未検証を隠さず、後続実装でinput検証とraw/effective優先をどう使うか提案。完全合法200ply・実historyなしdrawの生成が未完了でも人工fixtureを実局面と扱わない。license/model binary/provenance完全性は未確定、rootMITとtextlineageだけで配布可を認定しない。

受入れ/停止/報告:
重大な主張を支持/不支持/保留の根拠に分けたhandoff、input/sourcehash/再現command/raw/NodePID/exit/CPU/RSS/storage/期限遵守を保存。source原.5/.6はimmutable保持、自jobだけtimeout/kill/wait、他者job停止0。scope/時間/資源超過前に止め残件を未確認として報告。書込み停止、送信直前show目標/自子pause、backup sync、UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash /workspaces/quoridor/scripts/dev/research-team.sh report --to coordinator --issue quoridor-4lc --body-file /workspaces/quoridor/.worktree/ai-sigma/docs/reports/ai-sigma-critic-profile-parity.md。受入れ待ちin_progress、統括受入れ後本人close。目標issueは個別結果で閉じない。
