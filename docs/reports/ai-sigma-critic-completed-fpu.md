# .125 completed FPU 独立裁定

**未訪問Q因子の有限感度と指定4検索の再現を支持する。候補へのFPU実装・採用を、この結果から正当化する根拠は不足。actual_go=false。** 対局・holdout・build・取得・GPU・学習は0。受領13:11:50UTC、本人claim/開始報告accepted。処理13:31:50、新run13:28:50、提出13:41:50を維持した。

原123はdata Git `6e7e338c79e4be11f6a75a0df452e5df736e8ba9`、handoff `7bb4874`へbindした。tested `1ca0322`（golden9とprefix presearch失敗）、`33d2c13`（prefix6）、posthelper `b4285ab`を区別する。原handoff SHA406802072c15cd91c29b18cae369ec95ab08733f30b734c8c8d7eea01d72a549、停止SHAfebda7beccb674d8a4decd40cf76b6cb06220d3c8864c145593854f0d4343a80、必要30入力の前後hash一致。原source/model/kernelへの変更0。

ブラウザ内の独自checkerで全15完成検索を照合した。rootN32/edge和31、480backup/480手NN、terminal-noNN0。同5入力の初期features/logits/valueはA/B/C間で一致。10参照条件のtrueNode選択310件について、保存されたvisitCount/valueSumからparentQ、原未訪問Qと厳密Q0、visitedprior入力の範囲・単調性、最終child prior和を検査した。各選択時点の全child状態は保存されておらず、途中visitedprior和の全再構成は認定しない。候補parentQ欠測をrootNN値やedge平均で補完しない。数値は9固定参照rootと6動的自己整合を分けた。原参照golden6行のdepth欠測は保持する。

| 入力 | TV(A,B) | TV(A,C) | TV(B,C) | Action A/B/C |
| --- | ---: | ---: | ---: | --- |
| initial | 0 | 0 | 0 | 13/13/13 |
| asym-P2 | 1/31 | 2/31 | 1/31 | 67/67/67 |
| jump-P2 | 5/31 | 8/31 | 13/31 | 31/31/131 |
| prefix1 | 20/31 | 4/31 | 24/31 | 13/13/13 |
| prefix2 | 0 | 0 | 0 | 67/67/67 |

新primary `p125-count-r1`は結果前固定のprefix1 B→C、jump C→Bで4/4完成。128backup/128手NN、startup6を別分母として総134NN。Action・全root訪問分布・featuresは対応する原4行と厳密一致、rootNN差0。648bits/137出力、finite/strict[-1,1]、P2/固有合法順/Action別prior・softmax・訪問規約を独立検査した。新jump2rootは固定参照、prefix2rootは動的自己整合。全深部モデル一致ではない。後続 `p125-match-nn0`はブラウザ保存算術のみでmodel/session load・NN・新検索0。generic summaryのplanned4/completed0は追加4未実施を意味しないため別denominator記録で明示した。

B/Cは参照の未訪問Qだけを変えている。reduction=0ではparentQが残るため厳密Q0とは異なる。A/BはC、Q、精度、順序等の束で一因子ではない。prefix1で候補分布に近づく一方、asym/jumpでは離れる。A/Bは5入力すべて最終Actionが同一で、分布の近さを棋力や改善へ変換できない。5入力・各1検索、逆方向を見て選んだ独立4検索は代表標本でも正式holdoutでもない。したがって「FPUを実装すれば強くなる」は未判別であり、自動係数調整へ進む根拠にはしない。

新4行のwrapper wallはprefix B1392.950/C1231.760ms、jump C975.650/B1120.280ms。原jumpではB875.570/C1166.130msと逆向きで、順序・warm・OS・cleanup spanの交絡がある。これらはK32完成費であり500ms採用時の探索量や純NN速度比ではない。最小次案はcandidate policyを維持したまま、既119敗戦の少数保存rootで入力→初回eligibleCP・採用時completed数・自己待ちを参照と比較するNN0分析。探索規則差より先に、500ms内に利用できた探索量が差を説明するか判別する。これは新しい一律gateではなく次の配分候補である。

原admission launch0失敗1、presearch schema失敗1（NN/backup0）、transport16/実tree15、startup12を保持する。検査器例外をNN不一致や敗北へ変換しない。自己保存closure初回は実行中monitor/logをarchiveに含めたため復元照合が失敗した。原因・hash・exit1を保存し、対象から除いてNN0訂正、再照合成功。成功検索の反復・良好行置換は0。

13:16:26.236121UTCまでに実NN窓終了、13:20:13.491379までにNN0ブラウザ終了、13:26:21に本文前source/runtime-stop・hashafterを固定。両Modeldrop handles/activeNN0、各検索旧zero、main timer0、monitor callback待ち、inner forced controlledPID0とouter同identity wait/remainingunknown空を別保存した。自己抽出112identity現在不在、原自己before139と今回再抽出163は別分母として現在不在を確認。closure管理子の終了は別metadataで補足。現在不在を自然終了・全期間遵守へ格上げしない。

primary観測currentRSS peak1,565,765,632B、NN0 browser1,164,353,536B、全観測TID CPU[2]、ORT threads1/proxyfalse。40ms間の瞬間peak・終了子CPU・背景負荷・途中clock drift・内核CPU等値・独立cleanup spanは未保証。開始終了clock校正を保持し硬いOS保証へしない。新保存guard28MiB/critic combined112MiB内、追加予約0。最終保持量・archive/Git復元・command/PID/starttickは保存manifestを参照。

継承source-bindingsのmain/worker hashは基礎scriptでcount拡張後の配信bodyと異なるため、独自actual-served-source-bindingsに実配信6scriptとtested33d2c13の必要4source一致を固定した。原metadataを書換えない。primary後の自己diagnose変更は復元可能diffで保存し、primary source SHA ed3ed4b08b09aba0e694b5c111fc9d4155b71bca2fcbb3efe01e7d6588619817へ照合した。

再現commandは `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 120s taskset -c 2 python3 -B tools/ai-sigma-completed-fpu-independent/runner.py --config <config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <diagnose.cjs> --config <config>`。共有RuleA・原実行基盤を参照する独立性の限界を保持し、独立算術と元producerを区別した。必要証拠は [125保存正本](../../research-data/ai-sigma/125-completed-fpu-independent/archive-manifest.json)、[本文前停止](../../research-data/ai-sigma/125-completed-fpu-independent/runtime-source-stopped-before-report.json)。停止・backup/report後、受入れ担当coordinatorへ渡す。正式公平性/NI/Sigma同等/係数採用/goal・他者close0。
