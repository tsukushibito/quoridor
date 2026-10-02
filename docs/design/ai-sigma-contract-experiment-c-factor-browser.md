# SIGMA-C-FACTOR-BROWSER / quoridor-4lc.110 / 契約1・枠7

既experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746単独writerへ実依頼。現行枠7/common/experiment/研究実行記録規約と本書を全文継承、ready/show goal/self・pause/担当確認後110のみclaimし受領開始報告。107/109は停止・有限受入れ済み。ユーザー追加承認/root確認/新監督層は不要、旧期限・失敗・成績は変更しない。

## 問いと対照

94の提案（Git65b4252、SEARCH-POLICY/next-factor-plan）を実探索へ進める。候補PUCT Cだけ1.5→1.0を変え、等completed-backupの探索分布/Actionを比較する。旧snapshot46根の差は仮想次selectであり実MCTS/棋力結果ではない。初期・asymで先後交換が各W1L1だった107だけでC改善方向を予測しない。係数採用/正式NI/Sigma同等は今回発行しない。

baselineは107 tested ec4e92d/既immutable ORT pending Wasm、同fixed model・同features/value・Q0/FPU・sqrt(N+1)・seed1979/tie/finish/order・512node/depth24/caps・RuleA。モデル/NNkernelやその他探索規約を黙って変更しない。新C1研究moduleとC1.5 rebuildを同source/toolchain/flagsで作り、C定数一行だけが異なることをGit/diff/binary/設定で特定する。baseline rebuildが元の特徴/NN/prior/ABIと小実探索でparity成立してから因子へ進む。単にWasm.validate成功をbaseline parityとはしない。

## 所有と研究build

write scope: tools/ai-sigma-c-factor-browser/、自己 .artifacts/ai-sigma/resume-20261002/C-FACTOR-BROWSER/、research-data/ai-sigma/110-c-factor-browser/、docs/reports/ai-sigma-experiment-c-factor-browser.md。必要な共通分類修正に限りtools/ai-sigma-cp-frame/browser-main.jsを同experimentが編集してよい。旧107 runtimeはGit ec4e92dで不変に参照し、新版/Git/runに結果を分ける。他役source/92live/roles/registry/主製品rootlock/crates/modelには書込0。

研究local buildを現在配分として許可する。既tools/ai-sigma-ort-search/src/{lib,kernel}.rs、Cargo.toml/lock等の必要部分だけをGit/read-only参照し、最小private crate又は必要sourceを研究自域へ置く。共有quoridor-core等は元版を同定してread-only依存。cargo --offline --locked、既installed toolchain/wasm target、既cacheを用い、CARGO_TARGET_DIRを自己private targetへ固定する。root lock/cache/toolchainを更新せずnetwork/依存導入/download/GPU/train/host restart/製品main統合/push0。旧runnerの期限付きcommandをそのまま起動しない。未使用private build targetは必要binary/command/ログ/Git同定を残して所有停止後に整理できる。毎source/model/全履歴を複製しない。

build source/version、baseline/c1 artifact hash、model/Wasm/ORT/input/CPU/settingsを必要範囲で固定し、元/sharedfinal.wasmへ上書きしない。source/binary parity不成立やoffline dependency不足をC効果ゼロ・棋力負例にしない。小診断/原因修正は総予算内で反復可。成立しないまま重い同試行を続けず理由/代替を統括へ返す。

## ブラウザ内診断・分岐

main対局/採用/合法性/勝敗/時計、Worker探索+SAB、外Node起動監視終了後保存を維持。Node審判/毎CP binding/時計換算/必須Node事後replayを復活させない。

最初に109指摘の同時SAB FAULTとbrowser late/Judge/取消/外部abortの分類を小browser mockで明文化・修正する。全原因を別flagsに保持し、shared FAULTだけでbrowser遅延/Judge故障をengine lossへ上書きしない。因果時刻/責任が不明な同時事象は共通基盤unfinishedとして保留できる。新分類方針を結果前に固定、旧4gameは再分類しない。この共通修正は両係数に同じ版で適用し、係数因子の効果と混ぜない。原Worker停止超過9/end drift未測定を修復済みとしない。

baseline/C1.5 rebuildで固定initial/asym-P2/jump-P2の必要root特徴648bits/NN137/finite/strict[-1,1]/Action-P2/固有合法順/prior・対応固定参照abs1e-4+rtol1e-4、実raw ABI/owned stopと少数完成探索のparityをbrowser内確認。C1は同数値/合法/ABIを確認するが変更後全探索のActionをbaselineと同じに要求しない。

等completed対照は同固定3context×候補baseline/C1の6検索、root展開を含むK=32 completed backupを結果前登録（名目192backup）。N/sim/root edge和=sim−1を同規約で検査し、raw Sigma loop32と等しいと呼ばない。NNcalls/選択Action・root訪問分布/entropy/depth/cap/finish・実時間と停止を保存、terminal/noNN backupは別に数える。片方がKへ到達しなければ未成立/未完了として保持し、途中CPをK32成功へ置換しない。K32は探索方針の感度対照で、500ms実時間評価とは別条件。count実験のbrowser guard/timeoutと完了条件は実行前に明記し、進行中NNの強制中断/硬いOS保証はしない。baseline/C1の順は固定AB/BA等で事前登録し、同一seed/model/同CPU[2]/threads1でheavyを直列化、tree/history/cacheを持ち込まない。

上記数値/機能が成立して現在残配分があれば、C1候補対固定Sigmaの診断initial色1→2/seed1979を結果前登録して2gameへ進めてよい。次固定asym-P2 pairも結果前登録して最大4game起動まで。実対局は同browser main/requested500ms/402新NNcutoff/D500/adopt411、旧107と同じ基本規約を新版条件として明記。compiled baselineに新同classification版を使った小動作確認を先にし、C1 WDLを旧107 baseline WDLへ正式統合・因果断定しない。C1に勝ち方向を期待して好成績だけ置換しない。全attempt/late/AI fault loss/infraunfinishedを残し、係数不採用や差なしも有効な報告。

必要root数値・合法動的main・全棋譜/責任・原因側stop/ACK/次t0・公開予定/実stampをブラウザ内で保存検査。開始/終了のbrowser-main/Worker clock校正を新runで記録し、旧runのdriftを遡及補完しない。API awaitをkernel時刻、ACKwallをCPUとしない。通常手採用は進行NN/ACK待ちにせず、相手探索t0は旧ownedzero後で原因側残費を転嫁しない。C1の小診断や係数一因子変化だけで正式公平性/NI/native-browser同等を認定しない。

## 現配分と終了

枠終了10:12:31/新重job10:02:31停止。今回処理は受領65分又は08:55Zの早い方、新runは処理5分前、提出受領75分又は09:05Zの早い方。途中にbuild可否/parity/等completed結果/診断重要結果を短く統括へ報告。既107の07時台期限を遡及延長しない。

純source/mock CPU0/RAM1guard896MiB/各60s総600s。buildはCPU[0]1logical/RAM3GiB currentRSSguard2.5GiB/CARGO_BUILD_JOBS=1/各600s総900s。Chrome全体はCPU[2]1logical/NNthreads1/RAM4GiBguard3.5GiB/各600s/NN重総1800s、warm/startup/失敗も課金。buildとNN heavyは同時起動しない。steward CPU0/RAM1との合計CPU4/RAM8内。機能/数値/対照の要求総100、診断game起動最大4は別計上。現在のpause/所有/外heavy停止を起動前確認。

保存private build512MiB guard448MiBとruntime/Git/data128MiB guard112MiBは既experiment entry2GiB内から配分、親12GiB増加0。起動前に現保持/有効未使用予約とtemp/target予測を確認、cache/Gitの実現在増分を二重計上しない。必要な小binaryを再現manifestと共にGit保存可、モデル/大target全体をGit複製しない。所有target/tempを整理しても旧必要ログ・旧成果を一括削除しない。

source/runtime停止→NN/model/全searchACK/timer/monitor callback/innercontrolledとouter wait/remainingを区別保存→必要data/Git archive/復元hash/本文/Beads backup→統括。停止版の主張に必要な独立確認は後で配分する。自proof/go発行0、新役/再委譲0。通常の修正ごとに新契約/一NN窓/一原因一回/全過去gateを要求しない。
