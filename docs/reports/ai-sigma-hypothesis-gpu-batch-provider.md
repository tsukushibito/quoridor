# Sigma GPU実batch常駐providerの数値・総route費 / quoridor-4lc.177

固定d790 folded graphの私有dynamicB版を常駐stdio providerとして実装し、B2/4/8・順序交換・1行置換の有限数値対応とID帰属が成立した。JSON/pipe/H2D/同期/D2H込みのB2応答中央値はCPU ORT serial 8.262791ms対GPU実batch 3.033639ms（中央値比2.72372）。現在176の3arenaには最大B2＋短い部分配送を候補として引き渡す。実自己対局の有効教師行/総時間、同K探索のπ・ラベル品質への効果はこの課題では未測定で、176のCPU生成をGPU待ちにしない。

## 版・受付・入力

親frame12（08:47:38→12:47:38UTC）、契約Git0b6267b8、本人177。受領09:07:55.138378UTC、Beads ready/show goal+selfで本人割当/no pause確認、claim09:08:09UTC、私有adapter/static実開始09:09:16.546248UTC。新heavy09:42:55.138/処理09:47:55.138/提出10:02:55.138、親期限と予算は変更しない。初期速報はcoordinator turn01a100f4-c2da-79d2-b08a-fde130bed55bへaccepted。受付・本人静的開始・科学開始は別。

科学source Git2ab642ce8c4e3cb03ffbbab1b620e569ac4ef7a1（初期NN0版b3d992cdea398ae70179c78d5abe469c62eaada7）、run batch-provider-r1。174 adapter SHA04d0e586538385b988ec5755923f9f6d37abb884431127c20402c7b37b63d067を私有copyし、先頭shapeと壁head viewだけB=1..8に対応。BN eval、mean/amax spatialのみ、83 f32initializer、21folded Conv W+b/残6BN、gpool2/5/8を保持。元state_dict捏造/BN逆算/他モデル/原174編集0。モデルmodels/experiments/ai-sigma/reference/sigma-pcr250/best.onnx SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。元ONNXは固定batch1のまま、Torch-folded-dynamicB-v1という別provider版である。

元174保存5fixture initial/asym-hv-p2/p2jump/prefix13/14の648f32bitsを参照。旧CPUORT/CUDA出力だけ小圧縮参照に保存し、モデル重複copy0。B2=[0,1]、B4=[1,2,3,4]、B8=[0,1,2,3,4,2,0,4]を結果前登録した。B8は5unique＋明示3repeatで、8種類の独立ゲーム局面ではない。新局面・学習教師・正式holdoutへの格上げ0。

## APIと最大1接続経路

provider.pyは1process/重み・ORT session保持のJSONL stdio。infoでmodelhash/device/version/settings/batch/counters、infer_batch({request_id,backend,items:[{id,features_bits648}]})で各IDの137 f32bits＋136 logits/value＋batchcostを返す。cudaは実1batch forward、cpuortはB個の固定batch1 serialで区別する。stopで最終counter/memory返却後exit。shape/finite/ID重複/B範囲を拒否し、512sample-equivalentを実行前に課金する。毎推論reload/ラベル救済/サイレント再接続0。

Node生成親がbroker.cjsを一つ所有し、各独立探索の1pending要求をFIFOで束ねる。初期案maxBatch2、flush target0.25ms（Node timer実遅延は未測）、足りない場合batch1を送る。stopはqueuedを拒否しin-flightを明示し、生成ownerが返却/破棄とchildwaitを管理する。NN0 mockで2ID対応、同search2重pending拒否、batch1部分配送、stop pending0を確認。まだ176へ接続していない。複数batch1をbatch8と呼ばず、MCTS選択/更新/K/温度をbrokerで変更しない。

## 物理入場・開始・回収

178 static-stop.json SHA cf5d209a248757472e3bfccb15c42bcb6ea712f0cd20e7160636500da84288ea、science_source_stopped/mock_PID3361539不在を現物で確認。09:15から監督next窓不足、09:18からownedによりモデルjob0で待機し、自然監督終了後だけ入場した。待機wallは科学費と分け、manager-current/stopに全延期を保持。静的・管理commandは短いNN0 reads/check/Git、job science wall4.456746秒。管理300秒の計算配分を待機時計のresetや科学180秒拡大に使っていない。

admission09:22:12.094998UTC：監督ownednull/次09:38:38.402、scheduler3352074/starttick27085893とloadedconfig bindingを確認。選択current processはscheduler/watchのみ（RSS163893248B）、この時点で176の実3arenaは観測されず、同時3arena稼働の実測保証ではない。将来CPU pool[0,2,4,6]/契約RAM合計7.5GiBで親8GiB以内の予測を分離し、現MemAvailable21080436736B、GPUfree10610MiB/computeownerなしを確認。物理12GiBを推論6GiB許可に拡大0、178/176 interrupt0。

モデルjob09:22:12.095183UTC開始→09:22:16.552UTC終了、CPU0単logical、Node-parent/1provider全子をsubreaper/RSS監視。manager3364491/starttick27184988、Node3370800（manager-stopのidentity）、provider3370811/starttick27227286、bootab5e66ac-12ce-49b0-ac55-afe05e3f5216。childwait/ownedremaining/unknownadopted空、exact provider PID不在、source hash/元174 hash不変を確認。正常exit0/guard停止0。

Torch2.14.0+cu130/ORT1.30.0/RTX3060、Torch/ORT intra/inter1、float32/eval/inference_mode、AMP/TF32/cuDNN benchmark無効、CUDA_CACHE_DISABLE1/offline/no-sync。ゲーム/学習/新依存/compile環境変更0。GPU170rows＋CPUORT135rows=305/512、CUDA46実forward（うちB1等）とCPUORT135serialforwardをinfo counter/rawから再集計した。

## 数値と実費

abs1e-4+rtol1e-4を結果前固定。新batch1 CUDA5行を旧CPUORT/CUDA保存出力に照合後、B2/4/8を新batch1基準へ照合、B8 reversed/1row置換でも順・ID・行独立性を確認した。全84 request/response・305行の137bits/float表現/shape/finite/value範囲をstdlib checkerで再読込み確認。全新GPU行対旧CPUORTの最大差6.198883e-6、対旧CUDA3.337860e-6。新CPUORT135行は旧CPUORT保存bits/値とexact一致。B8→新batch1最大差3.337860e-6、数値失敗0。これは有限tensor対応で、離散MCTS探索path/訪問分布の同一保証ではない。softmax rootpriorの微差とπ/タイブレークへの影響を次のsameK検証と分ける。

| B / 各warm1+steady8 | CPUORT serial中央値 ms | GPU実batch中央値 ms | CPU/GPU中央値比 | GPU steady8集計rows/sec |
| --- | ---: | ---: | ---: | ---: |
| 1 | 4.176488 | 3.410960 | 1.22443 | 271.947 |
| 2 | 8.262791 | 3.033639 | 2.72372 | 616.195 |
| 4 | 16.573163 | 3.812278 | 4.34731 | 1014.910 |
| 8 | 34.797069 | 5.064011 | 6.87144 | 1485.706 |

CPU steady8集計rows/secはB1/2/4/8順に217.879/239.559/241.202/231.192。中央値比と全8の集計を混同しない。全8応答・warm1・provider段別H2D/forward/sync/D2H/JSON encodeをresults.json/requests.jsonl.gzに保存。Nodeで要求JSON.stringify開始から応答JSON.parse完了までを総route費に含める。schema/ID再検算とraw記録は返却後だが、前要求のcompression負担は次要求と競合し得る。同環境同CPU0・同出力形式の有限測定で、instrumented providerのJSON二重encode計測も応答に含む。broker待ち/実MCTS/合法手生成/BFS/arena/ラベル保存は含まない。

cold spawn→info2132.712ms、内imports1757.364ms/ORTsession27.421ms/Torch graph91.068ms/CUDAcontext-upload210.871ms。初回B1 CUDA要求643.959ms、初回B2/4/8それぞれ20.643/23.780/11.779msを保存し、kernel初回費をsteadyへ隠していない。steady warm1はparity後の既warm状態。startup/warm/first-useは別課金、Torch compile API0。

peak owned RSS1346174976B<1.75GiB guard1879048192B。Torch CUDA peakallocated23154176B/peakreserved35651584B<6GiB、allocator current20162048B/reserved35651584Bをstopで記録。driver/context瞬間peak全量は未測でTorch値と混同しない。process終了後GPUfree10610MiB/used1499MiB・computeownerなし、入場前と同値。現物資源/CPUquiet窓が成立した有限1runであり、将来全owner無競合保証ではない。

## 採否と引渡し

最大1routeとしてmaxBatch2常駐provider＋単brokerを176ownerへcoordinator経由で候補引渡しする。3arenaではB8集約を前提にせず、queue実fill/待ちも含む小sameK教師生成を次の176配分で確認する。利益が残れば有効teacherrows/総時間の改善候補、無差/悪化/数値不足ならCPU生成継続・GPU教師採用0。現在のCPU baseline/176開始はこの結果をgateにしない。B2の2.72倍をゲーム/secや棋力へ読み替えず、Sigma NI/学習ready/最高棋力は未認定。

後続の変更範囲は176の私有provider接続/lineage metadata/停止ownerのみ。GPUprovider版/modelhash/B設定/queue/cancel/modeを保存し、同K/rootN/edge分母を確認する。CPU/GPU teacherラベルを無記録で混合せず、原173正式holdout198局は教師転用0。本課題は実自己対局を自動開始せず、資源・数量・停止をcoordinator/176既配分で決める。

## 再現・記録

NN0再検算: taskset -c 0 python3 -B tools/ai-sigma-gpu-batch-provider/verify.py。科学入口: taskset -c 0 python3 -B tools/ai-sigma-gpu-batch-provider/launch.py（これは新許可ではなく原runの再現command）。source-binding/preregister/model原参照/5input旧参照/saved174-outputs.json.gz、84件requests.jsonl.gz SHA542e2531b0e08308a070101f3ff2a9be1230e17d5882cc5ece5260f63ae219ca、results/verification/checker-replay/provider-owned/manager-stop/admissionを自域保持する。自己科学source/子停止後、少量in-memory subtreeGit・byte復元・会計・Beads backup・報告をhandoff.jsonで結ぶ。旧conservative15069811B減額0、experimentの確認unused4MiB移転だけを使う既20MiB reservation/guard19MiB、親12GiB増額0。受入closeはcoordinator、goal他者close0。
