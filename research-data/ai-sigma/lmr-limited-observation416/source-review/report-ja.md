# 416.3 固定observer／cold scout境界の独立確認

`source_clear=true`、blocker 0、ordinary finding 0。対象は source-STOP `f79617fb…`／binding `2f8e450d…` の固定差分と限定consumerだけである。実softwareの完了、数値結果、棋力、既定採用を認定していない。Main／Git／Cargo／対象ソースへの変更、targetのimport、tests／Search／model呼出しは0。

immutable Git `8c54ec630e253dc5b92604a52057b4978a8fea68` とbefore gzipからメモリ内で正確にforwardを適用し、三Rust postimage、Python `measurement_config` 関数、inverseを照合した。Pythonの関数外bytesは同一。選択FileRefの前後SHA／size／modeと再構成根拠は `selectedrefs.json`／`reconstruction-proof.json` に保存した。恒常source mirrorは作らず、読取用の一時source captureはhashを残して回収した。

| 確認境界             | 固定postimageの根拠と結論                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 元Searchと採取       | `alphabeta.rs:1967–2035`、`lmr_observation416.rs:112–242`。既存のeligible／distinct rank／qを使い、TTによる窓更新と先行兄弟の探索を経た直前alpha・beta、親STM、非root plyを保存する。H0は返値前の最初の重複しない枝を予約し、中断しても交換しない。H+は完了した最初のshallow fail-lowのみ。確認／full-windowは同じ手のstageとなり、distinct rankを増やさない。元の減深・通常深さ確認・PVS分岐は変更していない。                                                                   |
| 独立probe            | `lmr_observation416.rs:323–412`、`alphabeta.rs:3021–3038`。root呼出しが終わってから、各probe固有の空TT／continuation history／killerで共通childを一度だけ呼ぶ。元rootからcolour付きpathをchecked playで再構成し、weighted aggregate countを含む完全履歴・盤面・rules・total plyを照合する。元の非root plyと親視点の `[alpha,next_up(alpha)]` を渡し、符号反転は既存childが所有する。H0のd−2／d−1、H+のd−1−q／d−1を区別し、親の自動確認・反復深化・元sessionへの書戻しを加えない。 |
| terminal・復元・中断 | `alphabeta.rs:1509–1623, 3011–3120`。true goal／threefoldの優先、既存enter/control、NNUE advanceのterminal skip、canonical make／undoとboard/context/path/child slot復元を共用する。cancel／capでcold childを完了できなければ前回root snapshotを流用せず、value/boundは欠測。errorの仕事量もnull＋unknown-work件数で残す。                                                                                                                                                        |
| 入力・結果のconsumer | `measurement.rs:388–518, 1675–1874`。完全prefixを`from_prefix`でreplayし、先頭4手のopening countとは別にdivergence board／STM／total plyを照合する。12入力のprefix長は4～9で、opening長は全て4。rootのSearch時計・統計とcold invocation／child／nodesを分離する。各probeの100K cap、指定／完了深さ、親視点window bitsとUpper／Lower／Exact-or-UNKNOWNを保存する。                                                                                                                 |
| OFFと必要費用        | 通常入口は `Search::<false>`。追加記録hookはconst-false内で実行されず、runnerのobserver allocation／probe／追加時計もopt-inのlazy分岐内にある。OFFへ新しいsnapshot、履歴scan、heap、clockは入っていない。ONでは最大4親context＋pathのclone、固定6 frames／24 buckets、採取候補の重複確認、各probeのreplay／履歴照合／空1M TT準備が必要。実layout、copy量、RSS、速度利益は未測定である。                                                                                           |

H0/H+内で同じ親履歴＋actionを重複除外してから各slotの先頭を選ぶことは仕様と対応する。予約後の中断を別枝で埋める経路はない。最大は12 root＋48枝×2 scout＝108呼出し、21.6M search-node capであり、未選択slotや未実行probeを成功件数へ加えない。coverageの機会／開始／完了は採取枝数と別分母である。

1 ULP scoutの返値は親視点のboundであり、通常深さも子孫DepthRankを含む選択的推定である。cold probeの`pv`は呼び出した一手だけの記録で、全PVを再構成したものではない。空なのはTT／ordering状態であり、歴史的warm状態やprocess／model全体のcoldnessを再現する主張ではない。局所probeの仕事を元root速度や旧対局の原因へ変換できない。

新AI6定義とrunner2定義は、予約・欠測保持、H+条件と重複、stage窓／bound、非root cold呼出しと中断／error、opt-in拒否と入力replayを区別する。ON/OFF同値toyはD2であり、実Search中のeligible枝採取までを網羅する試験ではない。これはsource確認の範囲説明であり、成功suiteの再実行や追加資格を要求しない。

Rootからのsoftware事実は別に保持する。BUILDv1は既存Search fixtureのcfg field欠落でFAILED 6.918606266s、None追加はtest-only `6d2580f8`。BUILDv2では新AI6＋runner2とresearch ClippyがPASSした後、diagnostics Clippyが新testのinitializer形式を拒否してFAILED 22.657626481s。`6fdfa44f…`はinitializerのみで、assertions／productionは同じとの報告である。残るsoftwareのPASS、image、科学entryは本レビューから推定しない。

私有helperの初回patch-owner推測AssertionErrorと、参照一覧へ追記しながら走査した読取helperの誤りも保持した。後者は本人のexact childだけを停止し、guardianが直接wait/reap、handle close、fresh absenceを確認した。必要な未確認箇所だけを修正helperで読んだ。producerや成功assertionの再実行はない。元source-STOPの記録時刻は12:36:45.081209Z、dispatchにある12:36:45.066586Zとは別に保持し、上書きしない。

最終の実reader STOP／direct reap／fresh identity／TMP・leases・owned残存は `STOP.json`。連続peak RSS、全LLM／source／admin費はUNKNOWN。paused scopes、defaults、models、RAW／FAILED／既存費は変更していない。
