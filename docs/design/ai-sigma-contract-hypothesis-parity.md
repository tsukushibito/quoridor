# SIGMA-PARITY-PLAN / 試行1 / 契約版1

目標quoridor-4lc、子issue quoridor-4lc.6。hypothesis / 01a0f31c-2e4b-7170-82c5-69e1428c2418、報告先coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。
目標契約 docs/design/ai-sigma-research-goal.md 版1全文とAGENTS/common/hypothesis、team design、AI設計/storage policy/handoffを継承。今回自律開始権限の実依頼、追加サブエージェント0。
初期子issue quoridor-4lc.2の調査はcritic .4が固定6原文hashと重要規約/encoding/資源差を独立照合し支持。統括は.2を調査再現性の範囲で受入れる。新turnの開始時に目標/.2/.6をshowし、pauseなしなら自分所有.2だけ受入れ根拠を追記して本人close、その後.6をclaim。目標/.1や他担当issueをclose/claimしない。closeを追加研究実行の許可としない。

場所 /workspaces/quoridor/.worktree/ai-sigma、branch codex/ai-sigma。唯一の書込み docs/reports/ai-sigma-hypothesis-parity.md と .artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/ 以下の小さいJSON、原文text snapshot、生成script・manifest/log。Rust/製品/共有docs/registry/主checkoutは変更しない。モデルbinary/clone/依存取得/更新/build/対戦/学習は今回しない。

予算起動30分以内（報告保存を含む、最後3分を保存停止・backup/reportへ確保）、1CPU affinity0、RAM1GiB、GPU0、新規保存32MiB。各読取/Node試験は短いtimeout/メモリ制限。全体締切UTC2026-10-01T01:17:58.145139+00:00/JST10:17:58、18:20UTC頃残り約6時間58分。全体4CPU/8GiB/12GiB。同時は統括+experiment .5+あなたで3役。experimentは準備2CPU/測定1CPU・RAM4GiB・保存4GiB予約、あなた1CPU/1GiB。GPU/学習実行は0。正式測定窓で重い処理を始めず、ネットtext/readと短いNodeだけをCPU0で行う。全体新規保存実績はexperiment報告待ち、モデル取得まだ0、12GiBから4GiB予約と既存初期文書・起動reserveを控除した残枠を維持。

入力 docs/reports/ai-sigma-hypothesis-initial.md、docs/reports/ai-sigma-critic-comparison.md（SHA256 607618c36454a18bb4f9ba2ec954b074a58e82214648e7991f5030b8400c74cf）、docs/reports/ai-sigma-steward-initial.md、launch.json。Sigma固定commit 751186344fc52ad0c29bc65922e62c6fa915f006、ONNX docs/models_9x9/best.onnx（metadata 11663428 bytes、Git blob SHA1 f23802a83dc9054b5227da74b3771698854535f0）、PT runs/models_9x9_pcr/best.pt（metadata 11718115 bytes）。metadataを実SHA256と呼ばない。出所/ライセンスtext・export/checkpoint履歴の必要部分だけ一次資料で限定調査する。

問い1/受入れ:
モデル出所と配布条件に追加条件の証拠があるか。root MIT/license hash、モデルspecific資料/第三者pretrained由来の有無と未確認、export出所/PT対応、固定モデルURL/size/blobをmanifestに記録。根拠のない採用・配布許可の断定をしない。ローカル研究比較用取得と製品再配布を区別し、未確定情報を理由に合法なtext調査を止めない。モデルbinaryの実hash/graph/numerical parityは次契約で取得後に検証する前提として残す。モデル固有情報がない場合に網羅的不存在としない。

問い2/仮説/反証:
固定Sigma Web game.jsから規約/特徴/Actionのgolden fixtureが得られ、Rust側の変換を後続担当が独立実行できる。予測は合法prefixのreplayでP2/jump/反復/終局が再現される。参照の出力が想定と違うならコード読取仮説を修正し失敗条件を残す。Rustとの一致は今回未試験。root不正手拒否のみの共通審判は比較parityを満たさない。
統括は比較専用規約A（Rust研究contextをSigmaの3回目反復手禁止/200total ply/goal優先/合法手なしdrawに内部探索まで揃える）を次実装方針として選択。製品standard-2p-v1は保持する。初期参照はWeb NN-MCTSの機能を保持。native/ローカル最小比較はRust-native対固定Sigma-WebのローカルCPU対局と名称を固定し、C++ native成績の代替としない。

方法/固定条件:
固定commitのdocs/game.js等を小さいraw取得・hash保存し、既存Nodeのみで短い参照実行。16–32程度のgolden fixturesを可能な範囲で生成し、実行script/input/output/schema SHA256、合法prefix/盤面/壁anchor/残壁/手番/total ply/history-count key、合法directionと実着地点・Rust209写像、特徴648値とP2 permutation、terminal/resultをJSONに保存。モデル推論はしない。固定生成seed20261001、温度等の棋力データではない。fixturesは変換/規約診断であり正式棋力holdoutへ転用しない。
優先: 初期P1/P2、straight jump、後壁と盤端diagonal、壁遮断、H/V overlap/crossing・到達遮断・残壁、非対称壁/P2 feature、同board count1/2・simulation overlay・兄弟復帰、ply198/199/200とgoal優先。合法prefixで到達できない条件は検証専用synthetic contextと明記し合法replayデータと区別。全fixtureを無理に作って合法でない盤面をgoldenとしない。
Sigma136→Rust209は合法局面で方向から着地点へ、H8+a→81+a、V72+a→145+a。P2のcell y8-y、anchor y7-y、H/V segmentsの異なる反転を別記。写像injectivity/roundtripを参照側で実行できる範囲だけassert。history keyを正確なposition-countで記録、root二重count/兄弟history漏れ/200手をprefix後200とする誤りを捕まえるcaseを用意。
必要なら原文の取り込み/生成方法をscriptへ保存してfixtureから再生成できるようにする。参照コードの関数export等の最小adapter差分はfixture実行に限り記録し、AI探索の変更ではない。script/hashがないLLM手書きの期待値を独立検証の根拠としない。

停止/報告:
pause/異常/上限で自己processのみ停止しPID/exit確認、他者jobを止めない。期限内に不足が残れば範囲と理由を報告、上限超過を成功扱いしない。正式計測やNN動作は未実施と明記。書込み停止後handoff項目の報告を保存、送信直前show目標と自子、backup sync、UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash /workspaces/quoridor/scripts/dev/research-team.sh report --to coordinator --issue quoridor-4lc --body-file /workspaces/quoridor/.worktree/ai-sigma/docs/reports/ai-sigma-hypothesis-parity.md。状態正本はBeads、受入れ待ちin_progress、統括受入れ後本人close。
