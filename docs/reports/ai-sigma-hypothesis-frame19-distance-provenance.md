# 距離clip対tanhと極値leaf由来 / quoridor-4lc.244

**frame20 phase-v2の一回jobは冒頭fixtureで不成立となり、16条件は全NOT_RUN。clip／terminal由来とtanhの順位差はUNKNOWNのまま。** 原成功結果へ置換せず、MAX1を消費したため追加job・再実行・case/depth救済を行っていない。

原因は私有jump fixtureの表現仮定の誤りだった。共有RuleAのAction `direction` は単位の向きで、相手pawnを越える着地点を `_pawnDest` が2倍の変位で計算する。本fixtureは `Math.abs(a.direction[1])===2` を要求し失敗した。`game.js:_pawnDest` の静的読取で表現を確認した。合法集合・探索コア・NNUEの不一致、badmove、棋力敗北へ変換しない。修正ならP2の移動前後座標差又は `_pawnDest` の着地点を検査する必要があるが、今回sourceを変更して成功化したり再計算したりしていない。

## 旧枠と新実行を分ける

旧frame19は2026-10-05 00:52:46終了、旧244science入口00:29/stop00:32/save00:39、source45/管理180/科学90/MAX1を変更していない。旧turn `01a10967-683a-7ae0-b56f-bf0e2e47178b` のusageLimitExceeded/failed/idleとBeads244open・claim無し・自scope未作成は統括の有限観測。本turn01:06:41時点にも自域未存在を確認した。旧dispatchacceptedを科学開始とせず、旧body/rawfailure/源費の未確認分UNKNOWN、旧read保守45を保持する。旧科学NOT_STARTEDを新失敗へ付替えない。

新ユーザーframe20は2026-10-05 00:51:02–02:51:02。本人ready/show goal+self、本人assigned・pause無しを確認して244claim、phase20-v2の新scopeを作成し静的開始した。goalのBeadsラベルは読取時frame19のままだったが、親本文版20・明示ユーザー許可・正runtime config/contract/parent bindingで科学をadmitした。親/運用/ラベルを担当が編集していない。初公開toolとclaim/static報告は統括へ配送済み。

sourceと結果前登録は01:13:26 UTC固定、旧枠sourceに未来の成功を紐付けない。新保持予約は元2441MiBを継承し追加0。旧243のstatic60/科学0/予約、239/240/241等の旧費・UNKNOWN・個別期限・173/旧openedtest非選定を保持。

## 結果前に固定した仕事

元239の機械選択4case・fullprefix/position key/side/ply/history SHAをbindし、D_clip/D_tanh×depth1/2の16条件を固定。240停止正本SHA `445775e90e3c6f380852174b38278ee5a08a7ca8d144755f2e4f25884293f638`、compact SHA `2a4a5b4f4a5877afb0aab588ca5e466110b3c5bf2628f8870389567a12c1641c` は現物一致。元exact列は保存D条件のみ対応対象とし、weights/PT/datasetを読み込まず、NNUEのforwardは行わない。

係数は既weight-manifestのtrain-fit a/bとそのSHA、入力は元QF1のSTM distance/80。計算順を

```
ds0=f32(distance_self/80), ds1=f32(distance_opponent/80)
diff=f32(ds1-ds0)
u=f32(f32(a)+f32(f32(b)*diff))
D_clip=clamp(u,-1,1)
D_tanh=f32(Math.tanh(u))
```

と登録した。コードのq.inputは既に/80で返すため追加の/80やSTM交換を行わない。terminalはGOAL±1、200ply又は全合法なし0を先に返す。root-child各full window、Action順・strict-greater、全合法・RuleA/history・親復帰を維持し、元clip列へのabs1e-7+rtol1e-7対応を結果前固定。

深さはroot-child先が最大depth1なので、子内部は全合法を走査し、同値のmax/min leaf originを全て集約する実装とした。各edgeの符号反転でterminalWin/Lossを入れ替え、非終端はsaturated/unsaturated、preclip/clip/tanh範囲と伝播値・witnessの符号を保持する。訪問しただけの非極値leafは原因集合へ入れない。これは実装方式の説明であり、今回未開始の16条件について完全性PASSを主張しない。

冒頭fixtureは同一jobに含む6項目: f32旧clip式/端点、GOAL優先/200draw、全合法なしfallbackの小mock、P2/STM/jump/wall/親復帰、三回目反復の除外、由来集合の同値・符号伝播。fixtureにもprocessedを課金し合計guard65536、内85秒/guardian90秒、CPU4単1/RAM512MiB・familyguard448MiB、結果gzip上限98,304Bを固定。warm/新model/Torch/forward/学習/教師/testlabel/GPU/対局は0。

## 実admissionと一回job

01:13:57.464961 UTCのfresh admissionで、frame20 recovered loaded正本、scheduler478864/tick41516692、monitor478872/tick41516710/boot、config/contract/親SHA・monitor freshnessが一致した。自然ownedNone、次監督まで約516秒、90秒+30秒回収の空きが成立。current foreign scientificは0、管理祖先PID/tickをbindした。242の停止正本、全3background cleanup_complete/remaining[]と実科学のtracked/runner currentexact不在を確認し、100ms対局測定に競合していない。全host未来不在保証ではない。GPU問合せ・割当は0。

|項目|実記録|
|---|---|
|task/schema|frame20-distance-provenance-244-v2 / distance-provenance-v2|
|actual start|2026-10-05 01:13:57.468855 UTC|
|stop|01:13:57.536002 UTC|
|実CPU|番号4、単logical、管理も同affinity|
|job数・wall|1 / .07079585397150367秒、科学課金も同値|
|peak family RSS|74,387,456B|
|child PID/tick|493986 / 41585110|
|runner PID/tick|493909 / 41584811|
|exit / guardian reason|1 / null（child assertionで不成立）|
|保存結果|UNSETTLED、processed4、fixture3PASS/第四失敗|
|16条件|全NOT_RUN、完成exact列0|
|NN/GPU|0/0|
|回収|remaining[] / all_child_waited / current_exact_absent|

3PASSは固定数値式とtanh端点有限検査、GOAL/200draw、no-legal fallback mockまで。P2/jumpの第四fixtureが停止したため、その後のhistory/origin aggregationの検査は未実施。失敗fixture内で一部処理が済んでも項目全体をPASSにしない。tanh20のf32丸めは±1を返すことを有限確認し、一般にtanh非終端は端点にならないという保証にはしない。旧clip列対応、根の原因集合、同値解消・sourcegap/Action変化は全未観測。

guardianは専用task/schema/issue/16完成/NN0/capを目的識別する。今回はexit1なのでpurpose_identity_PASSはnullで、通常exitを別taskの成功へ読み替えていない。actual argv/sourceSHA/preregister/admission/stdout/原gzip/processを保存し、MAX1の停止規則を守った。

## 次最大1の判断

次案は**jump fixtureのAction表現を静的修正した別future runで、同じ16条件を一回診断すること**を保留候補として返す。現在の失敗は仮説の反証でなく検査器の不成立であり、clip仮説とterminal/horizon/historyの優先は更新できない。元成功や旧失敗の置換、今回budgetのreset、追加jobを自動開始しない。private修正と版bindは数分、科学は元と同CPU4/90秒/NN0を上界見積にし、新現在配分・runtime/current/保存を確認できる場合だけ実行対象になる。

この診断は対照Dの原因判別で、tanhの手の強さ・公平基準完成を認定するものではない。242の教師精度→同wall効用とは別の経路を保ち、現D式・seed・clock・sourceへmerge/interruption0。rootmean教師をminimaxへ再学習すること、history特徴、新教師・旧test再選定・新対局へ自動で進めない。極値由来が未観測である現在、NNUE leaf-target/historyへ一意原因を割り当てない。最高棋力目標は未達。

## 停止・保存

solewriterは tools/ai-sigma-frame19-distance-provenance/phase20-v2、research-data/ai-sigma/frame19-distance-provenance/phase20-v2と本report。失敗実source・preregister・元gzipを変更せず停止。新source-read上界45秒/管理180秒、旧read保守45別保持。最初forecast372,736B、予約1MiB/guard768KiB/forecast512KiBのまま、旧unknown減額/親追加0。必要uniqueGit/current bytes・stop・費・Beadsnotes/close/backup・最終handoff receiptは自域metadataに残す。旧frame19と新frame20の受付/claim/静的/actualscience/成立を分ける。
