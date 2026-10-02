# 144: 壁なし有限ラベルのAI感度診断

固定したP1-race/P2-corridorの両方で、候補通常K32・候補root1K1・固定Sigma通常K32はすべて認証winを選んだ。登録した全win出口に従い当尺度の同形式反復を終了し、candidate immutable Q0/C1.5と固定Sigmaを維持する。ラベルが合法手を区別できても、この2入力ではAI条件を区別しなかった。一般棋力、全depth十分、小改修への感度、正式NI/Sigma同等は未認定。

受領2026-10-02 19:46:03.934522 UTC。契約/選定b564b3f、初期登録51eb3e6、科学停止版1d96dd5。旧142の登録8466495/科学3866532/data9143e12/handoff63d46ddを区別し、必要generation2memberを実hashでbindした。143科学885eb8eの独自walk/別solverの全8区間・同input/Actionとheavy停止SHA e04c01113ca4556f32d35acd0fd47caf88e4708a50b12bbd882fcdca323aa5ebを参照した。元env candidate-r2をGitIDにしていない。143最終本文を追加gateにしなかった。

| case | 条件 | K/rootN | edge和 | NN | NNなし完成 | Rust Action / label | 認証区間 |
|---|---|---:|---:|---:|---:|---|---|
| P1-race | candidate normal | 32 | 31 | 5 | 27 | 67 / 0 | [1,1] |
| P1-race | candidate root1 | 1 | 0 | 1 | 0 | 67 / 0 | [1,1] |
| P1-race | reference normal | 32 | 31 | 7 | 25 | 67 / 0 | [1,1] |
| P2-corridor | reference normal | 32 | 31 | 6 | 26 | 13 / 1 | [1,1] |
| P2-corridor | candidate root1 | 1 | 0 | 1 | 0 | 13 / 1 | [1,1] |
| P2-corridor | candidate normal | 32 | 31 | 6 | 26 | 13 / 1 | [1,1] |

P1の実手は(4,6)→(4,7)、P2は(4,2)→(4,1)。小label index0/1とRust67/13は実legal action objectを介して対応した。P2ではlabel1がcanonical NN index0に回転する。root1は根展開1/edge0/NN1、通常候補は32sim、参照は根展開loop外+31loopでrootN32。完成130、手NN26、NNなし完成104、startup6/session2は別。候補53のterminal回数はsnapshot terminal node visits和を確認した。参照51は未変更uncapped経路とcompleted−NNからの分母であり、各backupのterminal stateは保存していない。KをNN/CPU/wallへ換算しない。

通常/root1とも最大priorの同手を選んだ。P1候補prior約.849862、P2約.885217。通常の訪問分布は異なり、P1参照は別手にも2訪問あるが最終手/有限payoffは同じ。したがってこの測定から係数修正・model/value原因を選べず、同形式の追加入力/反復を自動開始しない。次案は1つだけ、別の中盤局所手品質尺度をまずNN0で設計し、改善差を識別できる条件と不足を整理すること。静的≤60秒/CPU0/RAM1、NN/game/入力生成0を将来の見積とし、今回の実行許可にしない。

保存prefix32/33・history/key/side/pawns/壁0・648feature bits・全root合法集合をmain RuleAで再現。全6のfeatures exact、NN137 shape/finite/value strict[-1,1]、Action別prior/order/P2対応をbrowser内で確認した。同入力の候補/参照/root1の根NNの保存数値はexact一致（NNビット列の別保存なし）で、登録abs1e-4+rtol1e-4も満たす。新入力golden参照はない。共有RuleA、生成された壁なし2状態、有限depth6/minmaxラベルでありIID/holdout/WDL/game-theoretic oracleではない。深部一般数値一致は調べていない。

実装は元132のread-only count入口と自域薄いmain/worker adapter。元immutableWasm/固定Sigma coreを実serve hashでbindし、共有source/build/model変更0。2Worker/model session/control/generationを分離し、fresh tree/history要求を両旧zero後に直列開始。完成Actionは専用SABへ公開してmain bounded読取で照合した。count結果/zero通知後に採点する孤立診断で、通常500msの採用/相手t0経路は変更していない。API awaitはkernelCPUではなく、参照深さ・各旧discardイベント等の未保存欄は欠測とした。

全科学attempt6成功、unfinished/fault/unscored/未実施0。接続/warm/追加科学要求0。prelaunch設定key違いとadmission r1の静的command誤読はNN/Chrome0として保存し、admission例外後spawn0を維持した。修正は自域helperだけで、成功科学検索を再試行していない。`summary.Git`の原placeholderは不正確なのでGit版として採用せず、before/after sourcehashと1d96dd5の実source一致を正本にした。

全Chrome/init/startup/monitor heavy 12.595881秒（上限120、job90）、CPU[2]/ORT各1thread、observed currentRSS peak 1544.934MiB（guard5632）。managed static 0.285186秒。短い編集/管理commandの全PID/RSS/瞬間peak/費用は欠測。API/whole wrapperやmonitor負荷から性能改善・正式公平cycleは主張しない。開始/終了Workerclockを保存、途中drift/exactAtomicstoreは未測定。

科学source/NN/Model2/search/main timers-message/monitorcallbacksは本文前に停止・速報した。innercontrolled forced/waitとoutersole-root ownedwait/remainingunknown空を区別し、46 exact identity現在不在を確認した。現在不在を自然終了/全期間/全host保証にしない。最終保存helper停止は後述のhandoff正本へbindする。processing20:30/newheavy20:25/submission20:45、親枠9の期限と資源を維持した。

再現入口・設定・全要求・失敗・actual served hash・時計・資源・停止は `research-data/ai-sigma/144-wallless-ai-sensitivity/` と同課題archive manifestを参照。共有model/ORT/Wasmは参照しコピーしない。archiveを停止rawから生成して全member SHA/bytesを復元確認し、研究Git/Beads backup後coordinatorへ引渡す。goal/他者close、actual_go、政策採用0。
