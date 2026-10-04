# 同node終局・合法再利用の有限比較 / quoridor-4lc.237

主案は**完成depth rootbest-firstの同評価器比較を優先し、今回の完全stamp式node-context再利用を採用しない**。元Stateの合法cacheが効いた後のwrapperは小さく、mutation安全確認の費用が上回った。これは一方式の局所不支持であり、同関数内に既計算terminal結果を渡すこと一般の否定ではない。第一arenaへmoduleをmergeせず、主236の開始gateにしない。

## 受付・版・実行

frame19許可22:52:46–00:52:46、本人237ready/show goal+self/no pause/assigned→claim・静的開始。旧費/予約/未知量を維持。私有sourceは tools/ai-sigma-frame19-node-context/ のみ。State/RuleA/referenceはreadonlyで再用し、モデル・Torch・forward・train・teacher・test・GPUは0。APIの停止SHAは api-handoff.json、結果前版は preregister.json。

新科学fixture-cost-r1は2026-10-04T23:07:47.818539+00:00→2026-10-04T23:07:48.244474+00:00、exit0、CPU0単1、jobwall 0.425931s（60s各/科学180s内）、peak family RSS 121008128 B、全child wait・同PID/starttick exact不在。管理ancestorはadmissionへPIDtick束縛し、frame19 loaded parent/current正scheduler+monitor identity・新monitor・自然supervisorowned無し/次窓・実foreign compute無し・RAM・storageを開始直前に確認した。現在の点確認であり全host/全期間保証ではない。

## 独立artifactと品質

`createNodeContext(s,contextString)`は同nodeのterminalと非終局時の全legalを束縛する。`read(s,sameContext,{cancelled})`は同State identity/context、全履歴・side・depth・盤面・remaining・derived map/path・legalcacheのsnapshotを確認し、差・取消・disposeをtyped失効にする。返却terminal/Action配列はimmutable copy、policy/TT無し。goal/depthdrawでは原terminalと同じ優先でlegal=nullとし、no-legal drawを省略しない。

Stateにはrevision番号がないので、JSON完全stampとAction copyを安全確認費として含めた。旧cacheがmutation後もstaleになり得るため、観測された変化後のStateを黙ってrebindせず再構築要求とする。mainの別VM Stateはこのartifactのinstanceofを通らない。v1はmodule.r.Stateに限定し、mainがそのconstructorを再用するか、将来factory薄接続を別に検証する必要がある。固定RuleA source/未改変prototypeの条件であり、全transitive helperへの任意monkeypatchを保証しない。詳細 interface-limitations.json。現在のmain drop-in readyとは呼ばない。

55 checksは、結果前固定の32合法prefix、P1/P2 goal、ply200draw、履歴third repetitionでpawn全禁止/壁0によるno-legal draw、side/depth/history/rem/segments/anchors/maps/path/cache変化、clone identity、contextgeneration、取消/dispose、選択method変更、子next後親復帰、返却immutableを有限確認した。元RuleA依存を共有するため独立ルール完全証明ではない。32prefixは診断Stateであり新教師game収集ではない。

## 同仕事量と費用

同32Stateのreplayで「search terminal→非終局legal→D wrapperのterminal」を原経路とmodule create/read結果再利用で比較した。双方同じ合法数checksum=39530/round、全合法順・terminal/源map/history保存を確認。10回×32×4順序AB/BA/AB/BA、1280node訪問/arm。合法cacheは同様にcohort準備でpopulateし、準備と保存assertをtimerの外に分けた。module内部stampは費用に含めた。NN/distance数値計算・alpha-betaは測っていない。

| 費用 | 原wrapper | 完全stamp module |
| --- | ---: | ---: |
| replay合計 | 2.244456 ms | 230.692513 ms |
| cohort準備合計 | 27.997019 ms | 25.774798 ms |
| 両区間の合計 | 30.241475 ms | 256.467311 ms |

原replay各roundは0.463095/1.755656/0.011527/0.014178msと短く、JIT/inline/条件順/timerに敏感である。raw合計比102.78はarena倍率や排他的支配費として使わない。原・module双方のcold/cohort準備はばらつき、全jobwallは両arm・fixture・保存・管理を含む。成功値を補充再runで置換しない。それでも全stamp方式の追加230.69msは原wrapper削減より大きく、今回採用する総費根拠はない。

既terminal→展開の二呼出しはState cacheにより二重BFSではない。native.distanceのterm再確認もcache-hit wrapper費の可能性を残し、旧terminal inclusive335.668msから今回の節約を決めない。terminal/legal、next(copy/history/path)、q.input(map/feature)、full/delta、value、control/JSONは親子inclusive区間を排他的に加算しない。

## 競合選定と次一単位

rootbest-firstは前完成depthのbestを先頭へstable移動するだけで全合法を保持し、追加model/stamp無しでalpha早期更新・cutoff増を問える。原Action昇順対rootbest-firstを同評価器・固定root/depth/nodecapで測る現在236の配分を優先する。枝数・完成depthの増加は同wall棋力を保証せず、等値Action/fail-soft bound/未完depth discard/clock配送を別に記録する。

reuseはnodeごとのwrapper回数の定数削減、orderingは訪問subtree数減少の仮説であり、期待倍率は未測定。全validationstamp導入は10分程度の私有source/fixture費を要したが、今回総feeには静的read90s上界・管理180s上界・科学0.425931sとLLM elapsedを別扱いする。回収C=実装+資格+対照+失敗+保存に対するΔwholewallが今回正でなく、有限な回収局数を示せない。今TT/make-unmake/広いcache/policyへ自動移植しない。

次判断は主236の**同時間NNUE対Dと、同評価器ordering全費**を別に読むこと。ordering利益が無ければその小枝を止める。元wrapperが実arenaで有意な費用か、新しい低費用revision/所有lifetime保証を既sourceが持つと分かった時だけnodecontextを再検討する。今の完全stampを外して安全性を救済しない。新対局/計算をこの報告から自動開始しない。NNUE最高棋力・SigmaNIは未達。

新2MiBを既poolから振替、guard1.5MiB/forecast1MiB内にsource/結果/必要Git/tmp/残metadataを含める。旧未知減額・parent追加0。必要Git/currentbyte/defaultindex保持・source/child stop・Beads notes/backup後に有限引渡しする。
