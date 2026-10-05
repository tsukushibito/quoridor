# frame21: 2時間の研究再開と主問いの修正

ユーザーの明示指示「チームに伝えて作業を進めて。2時間枠で。」および追補「NNUEが棋力に貢献するかではなく、貢献していない原因は何か」を受けたrootからの実行委任。新枠の実行を許可する。

開始2026-10-05 08:37:54 UTC / 17:37:54 JST、終了10:37:54 UTC / 19:37:54 JST。準備で起点を取り直さない。新heavy入口10:27:54、監督scheduler/正owned停止10:32:54、monitor回収10:35:54、必要保存10:37:54 UTC。旧frame20と各runの失敗/期限/成績/累積は遡及変更しない。

## 主問いと選定

目標はNNUE型で最高棋力。距離以上の情報を学習できるNNUEの可能性を追う。現在の主問いは『期待される学習利益が棋力に現れていない原因は何か』。方式名による優越を証明済みとせず、教師の情報/探索量/分布、特徴の情報と尺度、学習の適合と汎化、value視点/終局校正/差分評価/探索接続、評価費と到達深度を競合原因として扱う。

距離評価・同初期未学習NNUE・凍結学習済NNUEの同Rust αβ/同資源・時間の比較は原因を識別する手段。機能確認用10step学生0W4LだけからNNUEの限界を判定しない。意味ある学習済checkpointの選択根拠/尺度/初期対照を特定し、保存予測・実探索・失敗局面が次判断を変える最小比較を統括が設計して実配分する。対局だけで原因が分からない時は同局面同depth/固定仕事と評価値を結び、速度と評価の質を分ける。旧distance clip非terminal飽和や旧2prefixの偏りを弱い対照・代表性へ持ち込まない。棋力主比較は拮抗した多様なopeningと色交換、偏った局面は別層能力診断。数量・思考時間は残費と判別力で選ぶ。全候補検証を対局入口にしない。

探索高速化は独立ownerで並行できる部分を必要時に配分するが、移行/基盤整備や速度だけを目標にしない。結果から学習改善/特徴/教師量・品質/探索の優先度を更新する。新生成・CPU学習は根拠ある低費用判別へ配分可、全面sweep/NI反復を固定工程にしない。到達節目は原因を狭める実観測と次の改善判断、学習済モデルの有用な同時間比較。

## 現在の正本と環境

main /workspaces/quoridor がコード・設計・運用正本。現役実装はRust crates/quoridor-{core,nnue,ai,inference,data,runner,wasm}、Python学習はpython/quoridor_training。docs/development/rust-ai.md、nnue-training.md、ai-research-code.md、docs/reports/ai-rust-migration.md と ai-retired-code-cleanup.md の現在手順を確認。quoridor-runner release・既ORT/CUDA/TensorRT resident経路を再用する。旧tools/ai-sigma-*、tools/nnue-training、Node研究経路/比較テストは削除済み。過去recipe復元や全コピー/mirrorを研究入口にしない。旧WTは凍結モデル/データの永続参照だけ。直接比較に具体的に必要な旧版のみ目的/撤去条件付きで保持、互換性維持は不要。Nodeは製品・品質用にのみ残る。ORT_DISABLE_TELEMETRY=1をframework import前に設定する。

## 所有と資源

親quoridor-4lcを継続する。統括は既savedを使い各課題をBeads wrapperで問い・owner・編集path・総予算・必要検証・終了へ具体化し実配送。必要な独立見解は選定に使い全役承認待ちは設けない。研究sourceの正確writer/未コミット作業を保護する。

既枠の上限を維持: 計算job合計CPU4 logical、研究aggregate RAM8GiB currentRSS、保持+有効未使用予約12GiB。GPU推論VRAM6GiB/job30分、実競合/回収確認。GPU学習は既累積2hの確認済み残だけ、残不明なら新GPU学習0。CPU学習可。旧予約/不明量/累積をresetしない。各owner現在量とforecastから確認済みunusedのみ配分/返却。host現物headroomと現在native admissionも守る。新モデル/依存/toolchain取得更新・有料cloud・製品統合/push/公開・未知削除0。

既saved6roleとrootのactive人数上限なし、同役二重起動/dispatch lock/正確turn/owner/pause/応答不明保護を維持。同model/effort/settingsを維持しidle taskはmain cwdを明示。長jobは既背景実行でIdle→完了通知を使いLLMpollを避ける。

親現行枠文書 docs/design/ai-sigma-continuation-20261001.md の版21・絶対期限/現役構成への置換は、統括から既steward92へ一度実委任。rootはその文書・92sourceを書かない。steward solewriterで現在mainのscheduler/monitor/guard sourceのbindingを更新し、旧正identity/owned停止を確認→validate→通常freshstart→実running/loadedを報告。period1200/max_turn_seconds=null、他人数gate0。旧guard/helperが削除済み研究ツールを呼ぶなら必要な現役管理経路への最小修復を行い、廃止経路の復活をしない。stale fatalを新run再発と混同せず応答不明は履歴/receipt確認、盲目retry/モデル変更/AppServer再起動/強制tick0。静的研究は運用全史をgateにしない。

監督には主問いの選定/異論の採否/費用成果の点検、stewardには枠内終了点検・整理/長期保守判断を配分。意味ある通知だけ。終了時の実報告・採否と未完了担当/次機会を残し自動延長しない。

既173正式198holdout非学習、開封testは新未見評価に読替えず設定選定に戻さない。棋力/最高目標/SigmaNIは未達のまま。結果と科学費/全管理未測費を区別し必要なGitデータとBeads backupを保存。

最初の報告は実担当/本人開始/選定根拠と現在parent binding、92稼働は成立後追報。受付をscience成功にしない。報告先は継続goal quoridor-4lc/root既active、root準備専用issueのcloseを通信gateにしない。通常詳細の追加承認不要、結果からこの枠内で次判断まで進める。
