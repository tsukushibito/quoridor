# SIGMA-TRUE-MEAN-FPU-SAVED-INDEPENDENT / quoridor-4lc.141

140のtrue node meanと未訪問Q変更の機構、6保存K32、原版と計測Q0の根CP parity、事前quality枝終了を有限支持する。棋力改善・普遍的FPU悪化・119敗因・通常500ms性能は未判別。現Q0/C1.5を維持してこの2状態のFPU反復を終了する判断は支持できる。142開始gateではなく、政策採用/actual_go/NI/Sigma同等を認定しない。

本人19:12:51.152964UTC受領、ready/show goal+self・本人担当・pause無し確認後141だけclaimし開始を統括へ報告。契約/選定Git85d447dd989bf981d5c36cf83bd3d972e3c5c6b0、親枠9。早側期限は処理19:37:51.152964、新command19:34:51.152964、提出19:47:51.152964UTC。自scopeだけ単独writer、原140/共有crates/モデル/過去成果/default index書込0、新NN/model-load/AIWorker/Chrome/Wasm実行/game/rollout/build/取得/GPU/委譲0。

測定25d673dcee7cde1516eb10445eb4611abebc20f7、dataa09a25566d5508caf36ebc9564096c5c0514524b、復元4d9f491、最終metadata648695cd68a8e9c0609deb649b9f08fc058cd3ceを区別してbindした。handoffc8b19af2fa918237b786474aac4f781fd2c18d7fb549a4f2616639e207e6bd68、stop16a3f57c2d38ebe046d364145ed292355ad352e164494791ba83d84db9e0c136、archive1fd8e4483e0e95b7f42ec92b2898a88d717e31f0de5b33e04751019fff69c427を現物照合。必要canonicalの最終Git blob一致と必要archive member SHA/sizeをstream照合し、原raw/archiveの複製・全展開は行っていない。

独自Python算術2022項目は全通過。原集計helperを呼び出して成功扱いにはしていない。全6行が事前順序で完遂し、各K32/rootN32/edge31/手NN32、合計192手NN、実非終端でterminal-noNN0。startup保存6行各NN1と専用session2は別分母。両model digest一致・ORT threads1/proxyfalseを保存receiptから照合した。同KでもCPU・wall・計測負荷・500ms棋力の同等条件にはならない。

| 入力 | 原版/計測Q0 Action | FPU Action | Q0/FPU深さ | 訪問TV | Q0/FPU根未訪問選択 | 共有選定node/各8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| input3・totalply13 | 161 | 133 | 3 / 6 | 19/31 | 20 / 3 | 5 |
| input4・totalply21 | 32 | 118 | 3 / 8 | 25/31 | 29 / 6 | 4 |

原版と計測Q0は各入力の全32根CPでAction/訪問/prior/edge value/NN/深さ/caps/fallbackが厳密一致し、初期features/logits/valueも一致した。全192CPについて完成量とfinishのvisit→prior→seed tie規約を独自再算した。原版のtrue parent meanは未保存であり、根NN値や平均edgeから補完していない。

Q0/FPUの実selectはinput3で50/101、input4で34/95、全280。実node visit ledgerを各f32加算・訪問1増分で再構成し、各selection以前のN/sum、祖先手番による符号、訪問済みoriginal prior和を照合した。途中CPはtree本文が空なので、最終保存priorと各選択・backup ledgerからその時点のedge N/valueを再構成し、全合法edgeのPUCT得点とseed1979 tieを独自に比較した。単に保存されたchosen scoreだけを追認していない。

input3の最初の根分岐は完了4回後。両条件ともmean=-0.413908184、訪問済prior和=0.569146454、FPU=-0.564791799だった。Q0は未訪問132をscore0.193553716で選び、FPUは訪問済161をscore0.042686701で選んだ。input4は完了3回後、同mean=-0.676095307/同prior和0.316291928で、Q0の未訪問135からFPUの訪問済42へ分岐した。既訪問Qを変えず未訪問Qを下げたため、初期の広い探索から既訪問枝へ配分が移る有限例である。最終mean上昇・entropy低下・候補分布への接近を手品質改善の尺度にはしない。

Node VMの保存解析3949項目も通過。共有RuleAで合法prefix、key/history、P2、totalply13/21・壁残6,7/4,5を再構成。全6rootと各Q0/FPUの根＋先着7葉についてpath合法性、features648/logits136＋value、finite/strict[-1,1]、P2方向/壁anchor変換、candidate固有sorted legal順、Action別priorを独自算術で確認した。mixed abs1e-4+rtol1e-4内、最大prior誤差9.40615e-7。共有nodeのfeatures/side/NNは一致、未共有は各3/4node。固定中盤goldenは無く、RuleA・特徴実装の共有による独立性限界がある。全deep NNや一般ルール保証へ外挿しない。

private5source/lock、Q0/FPU2Wasm必要hash、元immutable bytes、必要共有libraryのcurrent hash/mtimeと7保存patchを照合した。両private buildは同source/toolchain/RUSTFLAGS/lockで、FPU側だけfeature flagを追加。source上の政策差はselect未訪問Qの0→trueMean-.2*sqrt(visitedOriginalPriorSum)。訪問済Q/C1.5/N/tie/order/finish/capsは同じで、true mean加算・traceは両条件に共通。これは未訪問Q0との一因子比較であり、fpuReduction=0との比較ではない。元132baseline bytesと原版対Q0 parityは有限根拠だが、計測JSON/trace費用の無影響は未校正。

Git-only再構成は不足する。共有crateには既未Git変更があり、保存patch/current bytesは一致、現在mtimeはprivate buildより前だが、build全期間の依存read auditではない。未追跡profiling sourceの必要hash、--libではbuildされないtest/binとlibraryを区別した。browser独立fetchdigestも欠測。source前後hash一致や現在mtimeでこれらを埋めず、新buildや共有source修復を要求しない。

保存NN0Wasm人工fixtureは実中盤とは別。初期根/async/resume重複拒否/terminal-noNN/深さ・node cap/pseudo leaf/N0/syncのsourceと保存visit増分・祖先符号を確認した。actual nodeだけN/sumを増し、pseudo leafでは祖先だけを更新する。N0はmean欠測を保持しQ0 fallbackで除算しない。今回実中盤の選定枝は非終端なので、実探索terminal経路の独立観測を得たとは呼ばない。人工fixtureの再実行0。

input3 FPU133による全quality枝終了は結果前preregisterにあり、quality0を確認した。134のfixedSigma後続で161=[1,1]/133=[0,0]だった局所不利は、今回版を採用しない小さい根拠にはなるが、事後の2状態・後続policy依存で普遍的FPU弱さを表さない。input4の118は未評価で、悪手/loss扱いしない。終了条件により118の品質を新たに識別する情報は得ていない。

設計は「true meanと未訪問配分が実装どおり作用し、選択を変えるか」に答える。棋力選定への直接感度は弱い。最大1次判断案として、142で有限ラベルが非自明な手を区別できた場合にだけ、結果前に小改修の採否を変える基準を定め、その同入力でQ0と変更版の手品質を比較する案を返す。区別が無ければ尺度枝を終了する。これは新AI評価許可や142の開始gateではなく、一般中盤・長期棋力への外挿も認めない。

原NN前失敗とclosure Git-onlyassert失敗は保存して科学negativeへ変換しない。自己schema rows誤参照、r1の空途中tree IndexError、r2の7patchヘッダ形式誤比較を検査器側の修復として全attempt/log/sourcehashbeforeとともに保持。r3は通過、r4はstartup/model/finish検査を追加して通過し、有利な入力/成功行補充はない。

原Model2drop、search6 zero/privateABIzero、main timer-message0、monitor全callback待ち、inner forced/controlledとouter sole-root waited/remainingunknown0を各raw receiptから照合した。原117同boot identityは現在不在、source before/after必要hash一致・最終source停止。速報source準備activeを最終停止と同時点にしない。現在不在は自然終了/全期間/全host保証ではない。

本文前自己source停止・全管理job終了、観測91identity現在不在/readerror0/remaining0。管理合計9.936秒、CPU[0]単logical、最大観測currentRSS102,690,816B/guard448MiB。短いintake/schema/Git/停止保存commandは外側別費用で、管理値を全担当CPU費用としない。sample間の極短child identity/RSS・未管理command全期間は未記録。初期critic artifactcurrent79,572,992B＋forecast2MiBはcombined112MiB内、追加予約0・未知旧保持減額0。原正本削除0。自己15member archiveのstream復元一致を確認した。

再現入口は `python3 tools/ai-sigma-true-mean-fpu-saved-independent/managed.py <newrun> python3 tools/ai-sigma-true-mean-fpu-saved-independent/check.py` と同wrapper下の `node --max-old-space-size=192 tools/ai-sigma-true-mean-fpu-saved-independent/numeric.cjs`。既期限は延長せず、新配分内のみ起動する。[独立算術](../../research-data/ai-sigma/141-true-mean-fpu-saved-independent/independent-results.json)・[数値対応](../../research-data/ai-sigma/141-true-mean-fpu-saved-independent/independent-numeric.json)・[停止](../../research-data/ai-sigma/141-true-mean-fpu-saved-independent/runtime-source-stopped-before-report.json)・[失敗](../../research-data/ai-sigma/141-true-mean-fpu-saved-independent/failures.json)・[復元manifest](../../research-data/ai-sigma/141-true-mean-fpu-saved-independent/archive-manifest.json)。受入れcoordinator、goal/他者close0。
