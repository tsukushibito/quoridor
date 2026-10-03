# 独立K800保存費用検算

quoridor-4lc.182 / 契約1 / saved critic。受領2026-10-03 10:56:59UTC、claim・実静的開始はintake.jsonに保存。早側は速報11:06:59、新command11:13:59、処理11:16:59、提出11:26:59UTC。180の旧source/成績/期限は変えていない。

**有限支持**：保存全30slotはwarm6/steady24、rootN800/edge799、手NN24000/startup6別。主controller elapsedは現RustJSONbridge候補がnative-hosted fixedSigma-Web751186 JS参照より3入力すべて遅い。事前速度equivalence marginがないので、比と幅をそのまま報告する。言語そのもの、public Sigma C++、GPU、棋力・NI、全自己対局の倍率はこの結果から判定できない。

## 原rowsからの独立算術

archiveを全展開せず、必要6memberをstreamreadし、事前input manifestと30slotの順・engine・warm/steady・全statusを照合した。各入力はwarm C,R後、steady C,R,R,C,R,C,C,R、各engine4回、成功行の補充・除外はない。

| 入力 | Rust中央値 [min,max] 秒 | JS中央値 [min,max] 秒 | Rust/JS中央値比 | 対応pair比の[min,max] |
| --- | --- | --- | ---: | --- |
| initial-p1 | 7.192829 [6.835621,7.969448] | 5.439503 [4.775514,5.949743] | 1.322332 | [1.148894,1.496409] |
| asym-hv-p2 | 7.406863 [7.213097,7.450866] | 5.590052 [5.404923,6.224756] | 1.325008 | [1.190958,1.339064] |
| straight-jump-p2 | 7.225083 [6.894508,8.215755] | 5.877197 [5.566991,6.076107] | 1.229342 | [1.134692,1.378275] |

warmはRust/JSでinitial5.961135/5.367814、asym6.591418/5.882756、jump6.548038/6.341986秒。warmをsteady中央値へ混ぜていない。各fixture×engineの専用held session6件のcold session/startup/全init時間を別fieldに保持した。同一coreを使い、順序を対称化しても、小標本のhost変動・時間drift・cold影響を完全に除けない。中央値比とpair比中央値は別統計である。

各rowで、初回root NN backup1+799 simulationというK定義、非負整数訪問799、合法順、先頭最大訪問Action、rootmean=rootValueSum/800、rootValueSum=rootNN−ΣchildValueSumの符号を独自算術で確認した。NNactual=returned=800、terminal-noNN/discard/cache0、外CP1。全30のrootfeatures648/初根137f32bits・value/logitsはengine間でexact、Action/合法順/訪問もexact、rootmean差0。root edge prior/valueSumのf64最大abs差は1.3877787807814457e−17で、離散path差をtolで救済していない。

共有RuleAによるNN0の3開始prefix/root対応では、side/ply/history/features/合法順と全30rowが一致した。initial P1/ply0、asym P2/ply3、jump P2/ply7、Actionは13/129/31。ルールsourceはownerと共有するので別ルール実装による独立性ではない。初根NN137bitsの対応は同native backend内の保存対応であり、全800NN/深部探索pathやbackendを新実行して再認証していない。

## 時計・費用の解釈

主elapsedは単一controller hrtimeのsearch送信前t0から最終CP受信parse・合法/root量検査・structuredClone完了stampまで。全30rowで差算術とt0≤CP完成≤result受信を確認し、次t0は前result/zero受信以降だった。Python側epochへ換算していない。後処理は別field、全30のpost-CP cleanup合計63.388283ms。worker elapsedは副証拠。

Rustは各search内部2404往復：raw1/new1/begin800/resume800/checkpoint800/cancel1/free1。応答byteは入力ごと7,657,465 /7,713,254 /8,054,662。外finalOnlyでも内部checkpoint800が残る。steady bridge span中央値は2.081145 /1.894523 /1.510005秒。NN API中央値はRust3.914374 /4.146577 /4.258775秒、JS4.051296 /4.113313 /4.241432秒。APIはpipe内包で、bridge spanの排他性・kernelCPU帰属を保証していない。これらを足して排他的内訳や純言語差を作らない。checkpoint削減は実費根拠のある候補だが、差全体の原因確定ではない。

測定job196.368316秒、NN0 mock3.157246秒、記録済owned全attempt jobwall199.525562秒。主elapsed全30合計192.733529秒。差分にはinit/warmstartup/管理/記録/cleanup等が入り、排他的に配賦できない。static準備/Git/報告費はunknownであり0ではない。必要保存member・archive SHAと版ca7ddb93e21d26196e24db3438a2a2a86b4a7121のsource hashを照合し、handoff66b373bd/data5a979094と結び付けた。current nativebinary166dd0c4f5eef9cd02a189e9e8bb4811bd307f6545db83a07e7180ea410e96f8、model d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908dも保存bindingと一致する。現在hashだけで過去全期間の実使用を完全証明するものではない。ORT1.30 CPUExecutionProvider intra/inter1 SEQUENTIAL、pool[2]を保存init/processで有限照合した。

qualification null、monitor READY、6engine close/exit0、process exit0/remaining・unknown空、保存観測TID affinity[2]を照合した。初期化時の必要owned PID/starttickと現在不在を別fieldに保存。全host/全期間/自然終了・実kernelCPUcycle同値は宣言しない。旧失敗・unknown・個別期限を改変していない。

## 181の裁定と最大1方向

181の新契約を結果前条件として読む。new/oldの局所採用規則は3入力中2以上中央値≤.90、残入力≤1.05。teacher routeはnew/JS≤.95が2入力以上、全入力≤1.05ならnew、それ以外は既finalOnly JSという事前規則であり、180への後付marginではない。steady2回の中央値・幅で行う局所的配分判断であって、正式速度equivalenceの検定ではない。

**唯一の懸念・方向**：K800のnew/JS規則だけでは、K64・全手の適格教師行/総費の改善を保証しない。rootK、終端頻度、初期化、合法/履歴処理、記録費の比率が異なる。新route選択を暫定heuristicと明記し、既予定の同K64/同3seed old-new 6gameで、同教師政策・全status/打切り・π/z/lineage品質を保ったRjoint/全attempt jobwallが悪化するならproduction前のvetoとして既JS基準へ戻す方向をcoordinatorへ提案した。採否・fallbackは新結果前に固定し、新JS K64比較や速度診断の追加連鎖は義務にしない。new/oldのK64改善をnew/JS因果改善へ読み替えず、24production自体の有効行/総費を報告する。利益が不十分でも新24lineageと小CPU学習へ進める契約方針を支持する。

181の薄sourceは読取時snapshotに限定して参照した。resumeにsimulations/done/nn_callsがあり、beginのterminal-noNNはpending=false/done=falseでも1backupを進める。毎sim control-drainを維持してdoneまで進み、最終checkpointを1回にできる。beginの非NN応答にはsimulation数がないため、途中取消のcompletedは最終CPのactual rootNに対応しない可能性がある。部分取消/guard/stale tokenはtyped unknownとして扱い、Kcomplete成功や有効教師行へ昇格させない。root terminalはrootN0/NN0/Action nullで政策教師行なし、K1はedge0なのでπを正規化できず、fixedK64のπ/63とは別である。最終CP公開から取消/freeまでの古応答・世代の扱いも有限確認対象に残る。現snapshotの検討は181実装の最終受入れやwholegame保証ではない。

179のπ分母・P2・z・game split/holdout限界を再利用し、旧1409教師行を再検算していない。6benchmarkを学習へ混ぜず、新24は独立lineageで全fault/打切りを保持し、zunknownをdraw0へ救済しない。元train1188＋新trainのみで176checkpointを継続し、原val/新valのπCE・zMSEを別表示する方針を支持する。正式173 holdoutは学習へ転用しない。fit/有効行速度をSigmaNIへ変換しない。

## 本人資源・停止

新scope2MiBを既critic112MiB guard内のforecastへ計上し、旧未知88,190,086Bを減額せず親予約を増やしていない。CPU0単1、独立算術＋NN0 root replay約.719秒、保守static charge3秒/120秒、peak59,592,704BでRAM guard448MiB内。source/科学子終了と監督currentの限定確認を保存した。新NN/session/model load/ORT/torch/build/game/GPU/train/取得/再委譲は0。原180/181/source/result・親/役割/common/registryは編集していない。必要小Git保存・stream復元・Beads notes/backup後coordinatorへ引渡し、科学受入れ・closeはcoordinatorが行う。
