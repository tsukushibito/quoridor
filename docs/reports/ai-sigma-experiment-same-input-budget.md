# SIGMA-SAME-INPUT-BUDGET / quoridor-4lc.126

同入力のwarm2・steady16、計18要求すべてで合法完成手を採用した。候補の採用completed量は入力・反復で優劣が混在し、一貫した準備/throughput不足という説明は支持しない。政策は維持し、戦術・終端尺度又は深部規則の必要最小対照へ次配分を提案する。119全敗因、棋力改善、係数採用、正式公平性/NI/Sigma同等は未認定。

119の登録prefix1,2,3,7は「参照が両色勝った例」の事後選定であり代表/IID/holdoutではない。まず旧8初期根のprefix/key/features対応を確認した。旧採用backupの候補/参照は7/13、12/8、10/10、6/10で混在。元bodyに採用量がなく、採用sequenceと最後のprivate CP sequenceの一致に基づく保存根推定と、新SAB軽量markerを区別した。旧raw・成績は変更しない。

モデル・C1.5候補/固定Sigma C1/FPU.2・探索seed1979・order/tie/finish/caps・RuleAを固定。専用2Worker/保持2session、browser mainの時計/合法Judge/SAB採用、外Nodeの起動監視と終了後保存を維持。各要求は新tree/context/generationでT500/cutoff402/adopt411。孤立した費用診断のため各要求後に両zeroを確認して次へ進み、残NN重なりを除いた。実対局の相手t0旧ACK非前提は変更しない。詳細数値検査は採用/zero後で、採用は進行NN/ACKを待たない。

steady順はprefix1/3 C→R→R→C、prefix2/7 R→C→C→R。全行を保持し、有利行の再測定や差替えはない。

| prefix | 候補backup（2回） | 参照backup（2回） | C−R（対応反復） | 候補初回CP ms区間 | 参照初回CP ms区間 |
| --- | --- | --- | --- | --- | --- |
| 1 | 10, 11 | 9, 8 | +1, +3 | 41.19–41.42 / 53.11–53.34 | 34.32–34.53 / 50.22–50.43 |
| 2 | 9, 9 | 15, 11 | −6, −2 | 61.20–61.43 / 58.64–58.86 | 24.44–24.65 / 32.08–32.29 |
| 3 | 9, 9 | 9, 11 | 0, −2 | 76.83–77.06 / 63.33–63.55 | 40.94–41.15 / 49.80–50.01 |
| 7 | 15, 11 | 16, 8 | −1, +3 | 36.00–36.22 / 42.98–43.20 | 29.44–29.65 / 50.10–50.31 |

全steadyで両engineのpublic Actionは同じだった。prefix1/2/7はそれぞれpawn前進、prefix3は右方向。初回API awaitは候補21.87–50.09ms、参照15.47–39.89ms。初回CPは候補のほうが遅い7/8比較だがprefix7第2反復で逆転し、初回差は採用backupの一貫した低下へ結び付かない。API awaitを純NN内核/CPU、rootNを同仕事量へ換算しない。根準備→API入口の時計区間は保存したがRust/JS内部の独立準備spanは欠測。

warmはprefix1 C/R各1、backup8/13。全18の採用backup191、実手NN203（採用に未使用の旧返却を含む）、startup固定golden6は別分母。採用後返却discard11、新NN開始の確定観測0。候補sim=rootN（source規約からの推定）/edge和=sim−1、参照rootN=raw root_visits=loop+1/edge和=loopを明記。候補の直接tree rootN/parentQは未観測。全採用CPでbackup=cp.nn_calls、terminal-noNN backupの観測0、一般深部terminal挙動を保証しない。SAB採用sequence/visitsと最後のvalidated CPを束縛して量を算出した。exact Atomic store時刻は欠測。

結果前選定の8steady根（各入力両engine最初）でfeatures648bits一致・137rootNN混合閾値abs1e-4+rtol1e-4一致、最大差0。各engineの合法順/Action-P2/prior/finite/strict[-1,1]自己gateも通過。prefixには固定golden NN参照はなく、両engine一致と自己整合の有限結果。その他要求の自己gate、startup golden6と分母を分け、全深部NN一致を主張しない。

late/初回無し/fault/unfinished/未実施0、最大public stamp413.285ms。開始/終了Workerclockを保存し途中drift・硬いOS期限は未確認。4入力各2反復で統計的因果/一般公平性を認定しない。旧WDLやK32 wrapper中央値と統合しない。初回差と採用量混在、Action一致から、単一費用原因や自動C/FPU調整へ進まず、保存敗戦の最初のAction分岐に限定した小戦術/終端尺度・深部value/finish対照を次案として返す。今回その追加NN/対局は実施しない。

受領13:34:22、処理13:54:22/新run13:51:22/提出14:04:22。実run budget126-measure-r1、source Git5c6b54c6816d595752377355d7b0622dfca27b66（基準2d94ffe）、保存helper c7ccde6。puremock exit0、browser exit0/guard0、managed heavy22.283234秒/static .144560秒。Chrome親＋所有子currentRSS peak1,633,054,720B<5.5GiB、保存観測peak3,792,896B<56MiB、観測affinity逸脱0。短metadata・背景CPU/瞬間peakの全期間保証なし。終了後報告generatorのSyntaxErrorと欠file配送失敗を保持し修正、NN/科学runへの影響0。

本文前にModel2/drop/searchzero/main timer-message0/monitor callback waitを保存し、inner controlledとouter同identity wait/remainingunknown0を分離。79identity現在不在は自然終了/全期間回収保証ではない。停止SHA e70033ada52257106b227450432dc5516663de278b71115ea2a5ab70e13bb5b8。必要原source/model/Wasm/prefix afterhash不変。source/runtime停止後に必要archiveをstream復元SHA照合、Beads backupと統括報告。独立受入れ待ち、actual_go=false、対局0。

詳細: [全行結果](../../research-data/ai-sigma/126-same-input-budget/final-results.json)、[旧8根](../../research-data/ai-sigma/126-same-input-budget/old119-eight-root-evidence.json)、[量の根拠](../../research-data/ai-sigma/126-same-input-budget/measurement-provenance.json)、[停止](../../research-data/ai-sigma/126-same-input-budget/runtime-source-stopped-before-report.json)、[archive manifest](../../research-data/ai-sigma/126-same-input-budget/archive-manifest.json)。再現commandは各started/process記録に保存、新run設定でown runner.py --config <config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot own diagnose.cjs --config <config>。旧期限/保存pathへ直接再実行しない。
