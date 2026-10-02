# SIGMA-PLAYER-WORKERS / quoridor-4lc.112

契約1・枠7。受領08:57:20 UTC、処理09:45／新run09:40／提出09:55。**専用2Workerのbrowser機能7要求と動的4ply、探索用4局を完了した。相手入力を旧ACKから分離する有限動作を支持する。** 候補C1.5対固定Sigmaの探索結果は2勝0分2敗・合法goal4。旧107/110と統合せず、timer改善・正式公平性・NI・Sigma同等は認定しない。actual_go=false。

実game sourceは `3682ab7b520024735e79e42eea79c982897c3957`、最初の機能版は `11c994c5cd7276524463ba49e6299d928e729c94`。main/Worker/監視glueのみ新自域へ置いた。元97協調探索、immutable C1.5 Wasm SHA `1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01`、固定ONNX SHA `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d`、ORT1.21/各推論1thread、Q0/FPU/order/finish/seed1979/caps/RuleAは維持。C1研究variantは使用せず、build・取得・共有source変更0。

## 実装と安い確認

candidate/referenceそれぞれに固定engine bindingのWorker、model/session、SAB、共有世代control、clock、旧回収promiseを置いた。mainは手番側だけに新探索を送る。採用はSAB bounded read→browser合法性/局面更新→UTF8 body/stampで一回確定し、旧結果でbodyを更新しない。採用時の共有controlにより、WorkerのNN入口・candidate begin/resume・reference generation checkで旧仕事を抑止する。既開始NNの返却は記録し、旧世代のresume/backupや次手への再利用を拒否する。同期NN割込みは行わない。

相手への局面通知とt0は旧ACKや詳細CP解析を待たない。自Workerの次探索だけは自分の旧zero ACKを待ってからt0を取る。詳細CP/数値検査は進行後にbrowserで処理し、対局中の相手時計開始へ一律挿入しない。対局/run終了には両Worker回収を待つ。外Nodeは起動・外部監視・終了後回収保存のみで、毎手のNode審判/時計/CP binding/必須replayはない。

Node小mockで逆順messageのengine別解決、初回無し、完成手更新、確定後更新抑止、取消、旧世代拒否、相手開始が旧ACK前の枝、自Worker再開前の待ちを確認。実browser preflightではsecure/isolated/COOP-COEP、SAB/Atomics/Worker/依存、browser goal/RuleA判定と同routing小mockを確認した。ChromeはNN0でもRAM6/guard5.5へ分類した。

初回Node mockはroot packageのESM扱いでcontrolのCommonJS exportを取得できず失敗。自域fileを.cjsへ変更して修正、失敗は保存した。機能版の `ACK_known_at_next_input` は現在public後に採取していた不足を記録し、次版 `905af50` で実t0時点の観測へ訂正。旧行は変更していない。機能版のt0対前ACK時刻比較は別の保存値から算出可能。`3682ab7` は結果保存の全診断row複製を避ける変更で、必要rawをbrowser-resultへ一度保持する。

## 機能と診断結果

2session loadは同model digest/threads1/proxyfalseを確認。initial candidate→reference→candidate cancel、その同mainの動的4plyを結果前固定。7/7公開＝正常6合法＋取消null1、4ply非終局、最大public432.205ms。全body不変、root features/NN/prior検査、両Modeldrop/search zero、timer/monitor/inner/outer回収を確認した。

その後initialとasymの各候補色1→2/seed1979をpairごとに結果前登録し、4game capで停止した。

| 入力 | 候補色1 | 候補色2 | 公開/合法 | public最大 |
| --- | --- | --- | ---: | ---: |
| initial-p1 | goal L | goal W | 142/142 | 431.450ms |
| asym-hv-p2 | goal L | goal W | 156/156 | 446.730ms |

4局すべてbrowser合法goal終局。game公開298、late/初回無し/engine fault/infra unfinished0。機能を含む公開305＝正常合法304＋取消null1。固定参照root8／動的自己整合297、prior検査305を別計上する。startup3session×6=18、手内NN1261、実NN計1279。全深部NN一致や一般treeの証明ではない。

| 観測 | 機能7 | initial pair | asym pair |
| --- | ---: | ---: | ---: |
| 相手t0が旧ACK前 | 4 | 112 | 120 |
| 前API awaitが相手t0を跨ぐ保存区間 | 2 | 103 | 107 |
| 旧NN返却結果の棄却 | 2 | 103 | 108 |
| 公開後の新NN開始・確実観測 | 0 | 0 | 0 |
| 402後の新NN開始・確実/可能観測 | 0/0 | 0/0 | 0/0 |
| Worker停止 upper<=D / lower>D | 6/1 | 137/5 | 143/13 |
| ACKwall>500ms | 1 | 5 | 13 |

機能の取消後次自手で13.160msの自己回収待ちを保存。pairの自己待ち最大はinitial .005ms/asym .020ms。旧ACKより先に相手を始めても、自Worker重複・他世代再利用は確認されていない。API区間跨ぎはmain/各Workerの保存clock区間からの算術で、内核実行・CPU競合時間ではない。共有CPU[2]では残推論と相手探索が競合し得る。start/end校正を保存したが、途中drift、競合ゼロ、OS硬締切は保証しない。Worker停止時刻、ACK配送壁時計、採用500msを混同しない。

## 停止・保存・引渡し

111停止正本 SHA `84ae079918c3f7232987b8259807bcacd2e0ecf33b4c1154f8045582779e54de` と208 identity現在不在を確認し、各heavy起動前に外重Chrome/Cargo不在・自己前回収・headroomを保存した。pure mock＋browser4runのmanaged jobはexit0/guard0、全remaining/unknown0。両WorkerのModeldrop/search ACK、main timer、監視callback停止、inner controlled回収、outer owned waitを各runへ分けて保存した。

本文前の[停止正本](../../research-data/ai-sigma/112-player-workers/runtime-source-stopped-before-report.json) SHAは `25911f3e41ea771798fe5f5d358bc0f52c4bedc0c3b93bd1b7689ca5531adb90`、記録450identity現在不在。これは自然停止・全期間遵守ではない。最大current RSS1,751,785,472B／guard5,905,580,032B、保存観測peak29,396,992B／guard58,720,256B。ru_maxrss高水位、40ms瞬間peak・背景SMT・終了子CPU・初期短commandの観測欠測を別に残す。追加実行0。

[archive manifest](../../research-data/ai-sigma/112-player-workers/archive-manifest.json)は必要120ファイルのstream復元hash一致を記録。archive SHA `01f5ef08e29b9c056d5513feceff6377fa213083c6374a4aba432d74a75a4950`、2,179,671B。モデル/全source/旧rawは複製せず、110/111使用中binary/rawを変更していない。コード版、設定、全棋譜・応答・失敗・clock・所有をGit/archiveへ固定した。

開始・機能報告は通信受付を確認。initial途中報告と停止速報は宛先 `systemError` で拒否され、記録して有界再試行した。通信障害を研究不成立やpause解除へ変換しない。最終[handoff](../../research-data/ai-sigma/112-player-workers/handoff.json)とBeads112 notesを統括の読取先とし、停止版の世代棄却・非同期引渡し・合法棋譜・回収という有限主張を独立確認へ渡す。正式goや独立受入れを自己発行しない。
