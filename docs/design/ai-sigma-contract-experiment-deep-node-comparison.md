# SIGMA-DEEP-NODE-COMPARISON / quoridor-4lc.132 / 契約1・枠9

既experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親9/目標/common/experiment/記録規約全文を継承し、ready/show goal+self・pauseなし/本人担当後132のみclaim、受領開始報告。研究worktree /workspaces/quoridor/.worktree/ai-sigma。旧129 writer/実runtime停止受入れ済、同新scopeへ移る。

130P1を部分採用する。問いは、中盤の同入力で対応state/features/NN/value視点/terminal/backupの解釈に不一致があるか、同評価から探索配分と実選択Actionが分かれるか。119の有限弱さは初回CP/締切lossで説明できず、初期根同入力の出力/Actionは一致、123/125/126もActionが同じだった。129はroot1の最大priorだけで4ラベルpassして尺度枝を終了した。係数変更・参照分布への接近を目的にせず、今回結果で次判断を変える。同Kは同NN/CPU/wallではなく500ms棋力比較ではない。root-only/戦術尺度の再対局はしない。

入力は保存119 pair1-color1・pair2-color2の順、各開始prefixから新公開Actionを8手/16手適用後の4位置を結果前固定する。totalplyを新手数と混同しない。元生成prefix/history/key/手番/壁残数/終局をbrowser main RuleAで復元し、固定入力SHA/preregister/source/model/seed/条件順をNN前保存する。終端/欠損/非合法なら未実施のまま補充0。有利な局面へ結果後差替え0、事後敗戦線診断でIID/代表/holdoutではない。元119 pair1 Git8124d876、pair2 532c873、最終handoffd4ee35eaとarchive必要memberを区別し、raw/元sourceを変更しない。130最終handoff837f0bb/SHAf263e13068571d4a30fb653276f622dad377ffeffcd04e3c0c240a80c2cfd772、analysis/proposals/source-bindingを必要参照する。

A現candidate immutableC1.5/Q0/sqrt(N+1)/f32/seedfinish/候補順/cap512node/depth24、B固定Sigma C1/FPU.2/sqrt(parentN)/JS Number/first/temp0/原順/元node-depth capなし、同固定ONNX/ORT1.21.0 CPU・各1thread/seed1979を維持。2専用Worker・各model/session/世代/control/SABを分離、通常手番側だけ探索、browser main入力/局面/合法Action/結果、Node外起動/監視/終了後保存のみ。各count要求は自分と相手の旧zero後に孤立実施して競合を除く費用診断で、実gameの相手t0旧ACK非前提を変更しない。モデルはsession保持、木/cacheは要求ごとfresh。GPU/game/holdout/model変更/共有環境更新0。

根展開込みcompleted backup K32、各4入力各2engine=最大8検索。参照はroot展開loop外+31loop、候補32simという規約を実分母で確認、raw loop32だけ渡して等Kと呼ばない。入力順固定1〜4、条件順1/3 A→B、2/4 B→A。K未到達・数値/入力/trace不成立は未完了で途中CPを成功へ変更0。NN開始/完了/終端noNN/棄却/バックアップ/制限/深さ/Action/訪問TVを別に記録する。startup固定6は別、余分なwarm要求を入れない。

必要read-only traceを自域private copy/hookに追加できる。全source/rawコピーは不要。原kernel/sharedcrate/reference/modelは編集0。candidate private source/manifest/lock/既toolchain/flags/deps/immutableWasmの元bindingを確認し、計測専用compileが必要なら同offline/locked既依存・別targetで行う。baseline source→元binaryの対応が不明ならprivate baseline再buildのbytes照合等必要最小で確認し、独立再証明していない点を欠測に残す。新依存/モデル/共有target/host/toolchain変更0。計測は選択/評価/backup/finishを変更せず、実採用するprivate binary/servedsourceのhashと原差分を保存する。referenceも計測専用local adapterに限定し正式固定参照を置換0。

NN前のschema/API/tracecap/数値形/符号をmockで確認。最初の固定中盤入力だけ、各engine原版と計測版K8の最大4検索（名目32backup/最大32手NN）を計測parityの別分母として行い、公開CP/Action/訪問/NN/caps等の必要一致を確認する。parity失敗は計測修復であり棋力negativeではない。同scope総予算で普通にdebugできるが、成功K32行を好成績に差替えない。成功K32を不必要に全再実行0。計測parity不成立なら本8の実行へ進まず未完了理由を返す。

各検索でrootと完了評価/終端を最初に迎えた先着最大7unique nonroot node、計8nodeまでを事前選定する。共有nodeはcanonical board/sideとhistory/Action path/keyの対応を確認して比較し、位置keyだけでdraw/history依存を無視しない。trace選定後に都合のよいnodeへ差替えない。必要nodeの648feature bits/137NN/valueの葉手番、実node visits/評価valueと親child/edge valueSum/visitsのpre/post-backup、terminal/winner、経路Action/順序を実観測として保存する。candidateに存在しないparentQ/valueSumは欠測のまま、edge平均やrootNNで補完0。参照childQとcandidate親edgeQは視点を変換して対応し、直接数値を誤比較しない。共通訪問stateだけ対応、未共有は欠測。一般全deep一致/真ルール独立性を主張しない。NN0人工符号probeと実Wasm/runtime traceを区別する。trace不足なら不足として返しこのrun中に上限を結果後拡大しない。

root各8のfeature/NN finite shape/strict[-1,1]/Action対応prior/固有順/P2を必要検査し、新中盤にfixedgolden参照が無い点を明記する。同入力root/共有deep数値はabs1e-4+rtol1e-4を結果前固定、bit一致/許容差/不一致を区別する。features exact/history一致でなければ同評価とは呼ばない。API await・wholewrapperはkernelCPU/純NN比でなく、計測負荷とprepare/stop別span欠測を保持する。Actionが分かれてもA/Bは複数規則の束であり単独C/FPU因果は未特定。

出口：対応value/terminal/backup不一致なら正しさ修正候補を根拠付きで返し係数調整停止。同評価でAction差ならその分岐の一因子又は130P2手品質継続の別配分候補。訪問のみ差/同手なら分布一致を改善基準にせず係数採用停止。共有deep欠測/同評価同手なら同形式反復を終了、必要最小計測不足又はmodel/長期評価案へ。最大1後続案と不足、現政策維持の対照を返す。P2rolloutは今回未配分・対局0で、自動開始しない。問い自体の不足や異論も許可範囲報告へ返す。

単独writer tools/ai-sigma-deep-node-comparison/（必要private Rust source/manifest/traceadapterのみ）、.artifacts/ai-sigma/resume-20261002/DEEP-NODE-COMPARISON/、research-data/ai-sigma/132-deep-node-comparison/、docs/reports/ai-sigma-experiment-deep-node-comparison.md。契約coordinator所有、130/119/129/131原成果・共有source/crates/target/models/common/role/registry/92/main/defaultGitindexはreadonly。source差分/Git版/input/run/config/served binary/hash/command/開始終了/失敗/stopと最小rawを保存する。

静的/mock CPU0/RAM1guard896MiB/各60秒以下/累計300秒。private offline build CPU[0]1logical/jobs1、RAM4GiB currentRSSguard3.5、各300秒/累計600秒、Chrome/他研究heavyと直列。全browser（NN0含む）はCPU[2]1logical/ORT1thread/RAM6guard5.5/各job180秒・各count30秒/累計600秒。build+browser累計1200秒、失敗/init/monitor NN0も課金。保存512MiB guard448を既experiment entry2GiB内から配分、親追加予約0。RAM合計8GiB内、起動直前proc/exe+argv/未知・読取error failclosed・所有不明拒否と外heavy/available headroomを確認し、gate失敗後spawn0。現在不在とcontrolled/outerwaitは別に保存。未知旧保持量減額/使用中依存削除0。必要自域未使用buildのみ停止後整理できる。

処理は受領60分又は17:20UTC、新runは受領55分又は17:15UTC、提出は受領75分又は17:35UTCの早側。時計reset/旧run延長0。本文前にModel2/search/main/monitorcallback/innercontrolled/outerwait remainingunknown/現同identity/前後hashを保存しsource/runtime停止→必要Git復元/backup/report。未実施/不成立でも停止・記録・引渡しでclose可能。受入れcoordinator、必要主張の独立確認は最終停止版に必要範囲、全再実行gate0。親23:10:59新heavy停止/23:15:59監督/23:18:59monitor/23:20:59終了・CPU4/RAM8/保存12GiB不変。正式公平性/NI/Sigma同等/性能改善/係数採用/goal他者close0。
