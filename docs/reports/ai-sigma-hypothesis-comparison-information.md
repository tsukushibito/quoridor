# SIGMA-COMPARISON-INFORMATION / quoridor-4lc.121

hypothesis → coordinator、契約1・枠8。優先は**同入力の探索規則と完成評価量を分ける小診断**。119は比較感度が全く無いという説明を弱めたが、探索係数が敗因とは特定していない。現政策・固定Sigma・専用2Worker/SABを対照に保持する。119を変更・再対局せず、正式NI/Sigma同等・係数採用を認定しない。

先に問うべき不確実性は、①入力と評価尺度が改善を見分けるか、②同入力で規則か準備費・完成量か、③次の結果が実装/配分を変えるか。現路線維持の根拠は119で両色敗北を検出できたこと、同モデルの保存数値と既110/111の単因子探索感度を再利用できること。大きな再対局より少数の判別が安い。

## 保存算術の結果

独自Python NN0で旧117全6pairと新119全8pairを別集計した。117はW6L6、全6pairで同じ盤面側が勝ち、Xi全.5。119はW4L12、Xiは順に **0,0,0,.5,.5,.5,0,.5**、平均.25。pair1/2/3/7は参照が両色で勝ち、pair4/5/6/8は同じ盤面側が勝った。「色交換すれば必ず感度が得られる」「全pairが位置優位だけで決まる」のいずれも支持しない。119の有限条件での不利は保存支持するが、普遍的弱さ・Cの悪化ではない。

119のprefix既plyは4/5/8/9/12/13/16/17。全16局で `total ply−prefix ply=新公開数`、新公開合計764を確認した。17を新17手と扱わない。全8pairを保持し旧12局とは統合0。合法・多様・AI前固定は、均衡/IID/代表性の証明ではない。117の3局面×2seedも6独立局面ではなく、Xi分散0から同等や精密CIを推定しない。

119の手NN開始は候補3584/380公開=9.432回、参照4180/384=10.885回。startup48は別。採用CP完成NN中央値は候補pair別7–9、参照9–10。異なる対局状態・終端backup・棄却推論を含むため、同仕事量/CPU/純NN比や勝敗原因とはしない。中央値の平均を全手中央値へ換算していない。

根は読取前に「登録順先頭2pair、両色/両engine最初の要求」を固定し8根だけ読んだ。開始手番側の2組はboard/side/history/648featuresが一致、136logitsとvalueも完全一致、Action対応prior最大差は6.18e−7/1.59e−6。公開sequenceと保存CPを照合した。

| 同入力初期根 | 候補/参照 完成NN | 初回CP ms | 初回session API ms | 公開Action |
| --- | --- | --- | --- | --- |
| pair1・P1 | 7/13 | 95.755/45.020 | 53.925/42.940 | 13/13 |
| pair2・P2 | 12/8 | 55.110/95.200 | 39.545/73.980 | 67/67 |

2組ではモデル出力差の説明は弱まり、初回CP費用・完成量の優劣は逆転する。「候補は常に準備が遅い」はこの範囲でも成立しない。全対局の候補初回CP中央値が遅い事実とは両立する。他6根は最初の相手手後を含むので同入力対照に数えず、全深部数値・CPU等値・内核時間は未確認。実parentQ欠測をedge平均で補完0。

## 最大2つの次案

**P1を先に推奨。** 固定3golden＋119先頭2prefixに、両現政策をroot展開込みK32 completed backupで各1回。さらに参照コピーの未訪問Qだけ `parentQ−.2√visitedPriorSum → 0` とする（15検索/名目480backup）。C/order/finish/model/seedを保持し、参照原版を残す。これは `fpuReduction=0` と異なる。参照変更は診断専用で、正式参照を弱めない。真のparentN/valueSum/prior和、Action/訪問TV、NN回数、初回CPと全費用を記録する。94 sourceと110/111有限結果が根拠で、Cだけの再試行を自動優先しない。

同Kで政策差が小さく費用差が残れば**現政策続行・準備/wrapper費用へ配分変更**。未訪問Qだけの変更が参照分布を候補側へ動かすなら**正しいFPU実装を次の一因子候補へ変更**し、勝敗改善は未認定。両説明を分けられなければ**自動係数調整を中止**、必要なvalue/finish/deep-context対照を返す。全5入力で無反応なら有限FPU感度不支持、数値/入力不成立は効果0にしない。sameKはsameCPUではなく、samewallは費用と分岐量も含む別問い。writer25＋独立15分、CPU2/thread1、既browser RAM6GiB、runtime上限120秒を見積る。119停止後の別配分が必要。f32/JS、order、終端backup、既評価入力が交絡として残る。

**P2は評価尺度の代替。** 次の別契約で、AI前の盤面幾何規則から4合法near-goal prefixを固定し、深さ≤2/各20,000node上限の独立合法列挙で即勝ち/次手強制負け回避を認証する。現候補・固定参照・root1の意図的stress対照を各500ms、最大12根。勝敗の代わりに認証済み失着と完成量を測る。root1を普遍的弱者とは仮定せず、上限で未解決なら未解決のまま、補充しない。

候補だけ失着なら**具体的戦術/終端原因へ実装変更**、両側失着なら**共通モデル/探索の問いへ変更**、全pass/未解決なら**この尺度の拡張を中止**して現評価路線を維持する。均衡校正の全診断必須化はしない。設計20＋実装20＋独立15分、NN runtime120秒/既資源を見積る。near-goalの狭い範囲、共有RuleAの独立性、戦略棋力未確認が限界。

人工logistic算術では色交換後も側優位b=0/3/5で能力差への局所感度が.25/.04518/.006648へ下がる。機序の例で、実bの推定や評価感度不足の証明ではない。119の4両色負けを踏まえ、評価全体の棄却を先に行う根拠は不足している。

## 記録・停止

ready/show/pauseなし・本人割当確認後121のみclaim。初回RPC12:16:20.663183UTCを保守起点に、実時刻読取12:16:41も保持。処理12:41:20/newcommand12:38:20/提出12:51:20、reset/延長0。119測定Git8124d876/532c873と8保存summaryを参照し、停止速報SHA624c0728…3b3fを確認。初回受領時未着だった最終保存版は後着更新を分けて受領。data/report a5f3183、handoff d4ee35eaの現物/blob一致とSHA1cacd67d…6aeを確認、測定版とは区別した。122独立結果を先取りしない。候補kernelは119Git blob不在で参照helperが一度Git128になった。readonly実hashは94参照と一致するが、119binary独立bindingとは呼ばない。

2管理runはexit0、計.2975秒、観測parent+child RSS最大74,989,568B、TID CPU[0]、自己4 PID/starttick現在不在。本文前にruntime/checker-source停止と必要参照を保存した。NN/Chrome/engine/game/build/取得/委譲0。短読取/Git/Beadsの全PID/RSS/CPU・瞬間peakは欠測を保持し、全期間資源保証はしない。旧保持観測5,869,568Bを減額せず保守保持し今回分を加算、既16MiB予約/combined14MiB内。全旧archive/他owner台帳の現在量は未再測定、未使用予約と保持量を混同しない。最終自身量はmanifest。

再現は新出力runで `timeout 60s taskset -c 0 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B tools/ai-sigma-comparison-information/supervise.py <newrun> python3 -B tools/ai-sigma-comparison-information/check.py`。独立保存算術であり新browser replayではない。詳細：[算術/入力hash](../../research-data/ai-sigma/121-comparison-information/analysis.json)、[2案/決定分岐](../../research-data/ai-sigma/121-comparison-information/proposals.json)、[source](../../research-data/ai-sigma/121-comparison-information/source-references.json)、[自己停止](../../research-data/ai-sigma/121-comparison-information/runtime-source-stopped-before-report.json)。必要版/runはlocal Git/manifestへ。書込停止後backup/report、受入れcoordinator。前提への異論を含む提案で、actual_go=false、goal/他者close0。
