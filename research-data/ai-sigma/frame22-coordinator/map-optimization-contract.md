# frame22 NNUE全距離mapの共通bitparallel実装・同仕事比較

親quoridor-4lc/frame22 11:36:03–15:36:03 UTC、heavy15:26:03/正owned15:31:03/monitor15:34:03/保存15:36:03固定。担当critic、既saved sessionのみ。旧275/277の全費・失敗・capsを保持し新配分を別に記録。277 source/science停止と必要archive/引渡しを先に本人確認してから本scopeへ移る。close/全稿ACK待ちを入口に増やさない。

問い:277のactualchild 503/489新mapでは両goal whole81mapがadvance包摂費の66.73%だった。この有限callerの支配費をbitparallelで減らし、NNUE同depth/node探索の全費が改善するか。TTは初登録rootの短PVで未測、今回rootTT/鍵/history/orderingを変えない。core shortest-only u128の利益をwholemapへ転用認定せず、81距離materialize・遮断mask構築・cache更新を全て課金する。

今これを選ぶ理由はvalid low-cost source-bound profileが最大費を示し、特徴情報を落とさず共通経路演算を高速化できる可能性が高いこと。scratch最終比不安定でmain不採用、TT実sequence余地未測のまま改造する案は保留。教師安定性/表現/regularization選定は278別ownerで並行、速度で学習利益を代弁しない。

solewriter既managed WT /workspaces/quoridor/.worktree/frame21-search の crates/quoridor-core/src/position.rs（必要な同crate module/export/testのみ）と crates/quoridor-nnue/src/features.rs・必要NNUE tests、専用runner example/test、research-data/ai-sigma/frame22-map-efficiency/、docs/reports/ai-sigma-critic-frame22-map-efficiency.md。main編集/Git/index/commit0。研究正本mainのcurrent core/NNUEを結果前bindし、既WTの275/277私有scaffoldとは比較版を分ける。旧私有sourceは科学archiveとGitpointを保護、277停止sourcepoint保存後なら本owner範囲をcurrent mainから明示copyして基準を整合できる（index操作なし）。比較は同binaryのqueue oracle/controlとcandidate、又は結果前固定した2binaryの同条件。main sourceの別writer変更を取り込む際はpath/SHA再bind。

現在coreはshortest-only u128 maskを持ち、NNUEはfixed81queue両goal reverse BFS、Sigma入力mapは別caller。必要な共通core API/内部blocked-edge helperを設計し一実装へ寄せる。両goal81距離u8と不可達81、P1/P2/盤端/壁交差・重複・合法経路/terminal/jump/history/make-unmakeを保持。駒jumpはwall-only map計算へ混ぜないがcontextルールの回帰を省略しない。cacheの壁変更・駒手共有、distance f64/80→f32 STM順、sparseIDsとnative full/deltaを不変更。Sigma648 callerへ自動利益を認定せず今回移行が不要なら源0変更。T1/DAG prototypeへ恒常mirror追加なし。

最初に新algorithmのqueue独立oracle一致（全81値、両goal、固定壁geometry/unreachable/P2と合法replay）とScalar/SIMD/full-delta/親復帰を有限検査。必要品質を確認してから固定4prefix同depth2/nodecap2000等の現実的上界をpreregister、warm/steady順序を交互又は反転して比較。Action/value bits/nodes/TT/NN/countersと入力history復帰を保つ。同NN work品質と同時間探索効用は別。mask生成/map materialization/壁対駒cache hit費とwholejob秒を残す。比較が有望なら統括別owner source review後main採否、悪化/不安定なら旧経路互換を永久保持せず証拠だけ保存し採用見送り理由へ。自己testsは独立採用レビューを代替しない。

新明示総予算CPU3single/RAM1.5GiB、compile/test commandwall180秒、NN0 source/preparation commandwall180秒/management90秒、科学MAX3/総180秒/各hard60秒、nativeNN150000/processed500000（tests NNも累積に課金）、GPU0/train0/game0/newmodel0。複数条件と反転確認はこの総予算内でまとめ、毎run新issue/全コピー0。275/277の残NN・費をresetしない。新data/source/Git/temp2MiBを旧2758MiBの確認unusedから移転し2755+2771+本2=8MiB、不明をfree化しない。旧275実forecast3403776<5MiB、2771MiBは原保持。shared release追加forecast32MiBを旧275128MiBのnet45047808から確認unused内に束縛、旧WT8MiB再用/newWT0。最新親storage/unknown128MiB保持をcurrent+forecastで再確認、予測不足なら具体量を返し黙って拡大0。

現在runtime scheduler1233793/45593355・monitor1235182/45599721は参照pointで、heavy前本人current loaded/24hash・CPU/RSS/storage/pause/owner/identityをfreshadmit。273/274実scientificchildren終了報告は全未来free保証ではない。278 NN0処理や次教師診断・fitの固定計時と物理非競合を短報で調整し、人数gate/他ownerinterrupt0。long job既background ID/notesbackup→Idle→completion一度。

開始ready/showgoal+self/nopauseassigned→claim/本人開始と初期sourcebind短報。最初実装/検証14:10目安、計測/採否14:35、source科学stop14:45/必要保存14:55（親絶対期限内、不足時typed部分終了）。全手書きRust/Python/configをcurrent formatter/lintで整形、凍結source/比較データ書換0。全費/NN/分母/故障/未知/版/必要sourcepack stream復元・停止をhandoffし本人close/backup。追加user/root許可/全役ACKなし。
