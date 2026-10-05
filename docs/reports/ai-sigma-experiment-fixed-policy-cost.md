# 137 固定policy・同状態の費用境界診断

warm1＋steady3の全4要求が合法な完成手を採用した。同入力・同Kの保存CPではActionと根edge統計が一致し、steadyの採用可能backupは8/9/15、Actionは154/154/162となった。API await中央値の低下と完成量増加が同じsampleに現れたが、CPU/scheduling原因、純NN速度改善、119の敗因は特定できない。現政策を維持し、この状態の同形式反復は終了する。

本人受領2026-10-02 17:40:29.388935UTC、担当137のみclaim。処理18:15:29、新run18:10:29、提出18:25:29の早側期限を固定した。契約Git1c94c203、実測入口Git451f5007efc6c52f1e3055db2344525bdd6ffee2、run cost137-r2。原134 source6b79eca/data7af1635/handoffbd339e2・136 data d13bd5b5/handoff05d20e4を参照し、原成果・モデル・kernel・default indexは編集していない。

入力は134 group1 input3-rep1-Aの第3新公開手へ供給した1状態。保存group2対応根とkey/history/side/P1・legal prefix16ply・features648・根NN137がbit一致した。壁残5/5、totalply16。原archiveの必要memberと行indexをSHA照合し、browser内の通常RuleA手適用で再現した。履歴の挿入順とcanonical記録順を分け、mapのkey/countを確認した。新入力のfixedgoldenは無く、保存出力・自己整合との一致である。

2専用Worker/session/SAB/control/generationを保持し、両slotの実policyはfixedSigma C1/FPU.2/first/temp0/originalorder、固定ONNX/ORT1.21.0CPU・各1thread。通常探索は対象P1だけで、相手先読み無し。全要求fresh tree/context/history/cache、session/重みは保持。両旧zero後に次要求を開始する孤立費用診断であり、元対局の相手t0旧ACK非前提は変更していない。Nodeは外起動・監視・回収・終了保存のみ、毎手時計/審判/CP往復0。

| 要求 | 採用eligible backup | Action209 | 手NN API | 初回CP ms | 初回API await ms | API await中央値 ms | main準備 ms | 実採用 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| warm | 8 | 154 | 9 | 82.37 | 42.22 | 36.63 | 4.685 | 414.37 |
| sample1 | 8 | 154 | 9 | 68.16 | 45.42 | 38.03 | 0.920 | 411.21 |
| sample2 | 9 | 154 | 10 | 63.10 | 48.38 | 36.73 | 0.300 | 410.49 |
| sample3 | 15 | 162 | 16 | 44.33 | 27.60 | 20.88 | 0.215 | 410.56 |

全4started/completed_legal、未開始/初回無し/late/fault/infra0、追加機能要求/対局0。startup6・session2と手NN44は別分母。T500/cutoff402/adopt予定411、bounded2sampleを保持した。actual stampはtimer分解能・schedulingの観測で、exactAtomicstoreや硬いOS期限ではない。公開はACKやNN終了を待たず、全4の採用bodyを旧返却で変更しなかった。

根展開はloop外でbackup1、各loop1backupなので、採用rootN=8/8/9/15、loop/edge和=7/7/8/14を直接確認した。採用CPのterminal-noNNは0。全accepted SAB CP列はK1..8が全4要求でAction/根edge bit一致、K9はsample2/3で一致。旧134保存列との厳密な共通KのActionも全一致し、近隣K・補間・欠測補完はしていない。K1 Action40、K2..7 Action162、K8..13 Action154、sample3のK14/15は162。全深部state/NN一致は未確認。

kernel finish span数は8/8/10/16で、accepted SAB量と分けた。sample2 CP10、sample3 CP16はAFTER_CUTOFF拒否で、全CP本文は現計測では欠測。拒否sequence/時刻とfinish markerは保存したが、本文やAction/edgeを推定しない。warm/sample1は残API返却各1を棄却、採用後API残区間6.36/8.32ms。public→両zero待ち7.93/15.16/0.005/1.10ms、ACKwall422.40/426.36/409.15/411.70msはCPU時間ではない。初回root準備/API/完成公開・回収の境界は保存し、成功終了側で元rootFinished欄が無い場合は欠測を保持した。

所有TIDの162sampleでutime/stime（10ms tick）とschedstat runtime/runqueue(ns counter)を採取した。Worker/NN→TID直接bindingは取れず、main TID commがchromeのPID群をproxy集計した。exeをTID採取時に保存していない点と、消失threadの末尾・guardian自身のCPU終値欠測を残す。各dispatch→公開区間の内側sampleのみを使い、外端74.86+89.49/31.35+0.15/86.00+57.71/59.51+93.25msが欠測で、補間しない。

| 要求 | 内側sampleのChrome runtime ms | Chrome TID runqueue和 ms | 非Chrome所有TID runtime ms |
| --- | ---: | ---: | ---: |
| warm | 96.57 | 260.89 | 73.73 |
| sample1 | 143.21 | 313.44 | 113.33 |
| sample2 | 89.50 | 192.08 | 77.71 |
| sample3 | 141.06 | 146.33 | 17.52 |

この表は範囲長と欠測が異なる部分観測で、純NN CPU・全期間CPU・runqueueのwall待ちへ変換できない。Node/Beads observer、他Chrome thread、guardianの同CPU負荷があり、monitor周期wall中央値20.32ms・全period和12.03sもCPU消費そのものではない。readonly CPコピー/時刻追加の負荷は未校正。main準備短縮だけをbackup8→15の原因とはせず、API応答境界の関連までを有限支持する。

最大1後続案は、外側監視の実CPU帰属と観測負荷を揃えたAPI費用境界の一因子対照である。同入力・policy・modelを固定し、成功行を追加反復するのでなく、別配分で対照を結果前登録する。必要費用はstartup6＋最大2要求・browser90秒以内/CPU2/RAM6GiBの案。監視負荷を制御しても完成量/API差が残る、又は境界差が出ない場合はその費用原因案を棄却する。未着手であり、自動C/FPU調整・候補採用・棋力/NI/性能改善認定はしない。

安いmockは入力/schema/history不正の拒否、両fixedSigma dispatch、独立SAB/control、旧世代棄却、自次手回収、相手時計の旧ACK非依存、分類を確認した。cost137-r1はprotocolmock起動commandをconfigと誤読してadmission失敗、spawn0。修復後のr2だけ実NNを起動した。集計analysis1のoptional rootFinished KeyErrorもNN0の検査器失敗として保存し、欠測扱いへ修復した。科学成功要求の置換は0。

135 stopSHA40ff68ec…1985cと45記録identityの現在不在を、17:53:39起動直前に確認した。外heavy0、MemAvailable21,298,601,984B、自己current593,920B＋forecast16MiB、guard56MiB成立後だけspawn。重runtime20.428637秒/180秒、全所有Chrome＋Node＋guardian currentRSS最大1,610,956,800B/guard5.5GiB、観測TID affinity[2]。static/mock/集計はCPU0・RAM1GiB内。短い管理コマンドの全期間RSS/PIDは未記録で、完全資源保証へ格上げしない。

最後heavyは17:53:59.640951UTC。Model2 handles/activeNN0、search4 ACKzero、main timer/message0、monitor callback待ち/タイマー停止を保存した。inner controlled cleanup forcedとouter sole-root ownedwait/remainingunknown0、現在sameidentity不在、測定source前後hash一致は別証拠であり、自然終了/全host/全期間停止の証明ではない。最終source/runtime停止JSON、全run/失敗/clock/資源/CP列/TID観測は保存archiveとmanifestで復元確認し、研究GitとBeads backupからcoordinatorへ引き渡す。現保存と未使用予約・過去peakを分け、既experiment entry2GiBから64MiBを使用、親追加予約0、他者/共有/原成果削除0。

保存正本は[analysis.json](../../research-data/ai-sigma/137-fixed-policy-cost/analysis.json)、[入力とsource/member binding](../../research-data/ai-sigma/137-fixed-policy-cost/input-source-binding.json)、[preregister](../../research-data/ai-sigma/137-fixed-policy-cost/preregister.json)、[最終停止](../../research-data/ai-sigma/137-fixed-policy-cost/runtime-source-stopped-before-report.json)、[archive manifest](../../research-data/ai-sigma/137-fixed-policy-cost/archive-manifest.json)。受入れはcoordinatorへ委ね、目標/他者issueをcloseしない。
