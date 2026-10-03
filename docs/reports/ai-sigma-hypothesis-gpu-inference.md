# 固定Sigma folded ONNXのCPU/GPU有限比較 / quoridor-4lc.174

固定ONNX d790の83 FLOAT initializerをそのまま私有Torch adapterへ読み込み、保存5入力のCPU ORT・Torch CPU・Torch CUDA比較が全件成立した。初期単入力のsteady8応答中央値はCPU ORT 3.5707745ms、Torch CPU 6.005743ms、Torch CUDA 2.100652ms。CPU ORT/CUDAの中央値比は1.69984だが、Rust探索・実provider IPCを含むnative速度倍率ではない。主CPU正式評価の版・結果を変更せず、GPUは次の教師生成provider候補とする。

## 版・入力・受付と実開始

親quoridor-4lc/版11、契約1 Git58006321e5cc3230d0290f670a2d68d278d2a8b1、未来未実行窓を訂正した契約2 Git38054955b40070d07f16d400d41adb6b71fd85a6。受領06:45:35.781138UTC、本人claim/静的開始06:45:40UTCを保持。171 source停止・必要mapping・Gitをintake.jsonで照合済み。新heavy07:58/科学処理08:02/提出08:10、親08:15:21終了は変更しない。

科学ソースGit1885bb3c651685d602bd48db74e85e7386242123、run folded-gpu-r1。旧NN0待機版Git8f671de2b9fbc6162bf2b5361bc77cdc14a75e5eはモデル実行0のまま停止し、wait-r1-stop.jsonを保持。最初は監督owned、次に173停止handoffのパス違いで延期した。本人がepoch1-stop.jsonと旧quality process.jsonの全tracked PID/starttick不在を確認し、自域の入場判定だけ修正した。科学条件・adapter・入力・閾値は変更していない。

モデルはmodels/experiments/ai-sigma/reference/sigma-pcr250/best.onnx、SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。元重み・raw graphの保存コピー0。171 graph-evidence.jsonとその出所を参照し、N9/F128/R10、gpool zero-based2/5/8、179node、83initializer、21 folded Conv W+bと残6BNを扱う。元state_dict復元・BN逆算・元dual_network副作用import0。initializerのraw f32bytesとTorch CPU入力配列のhash一致を実コードで確認した。

入力は160 reference fixtureの元648 f32bitsを保持したinitial-p1/asym-hv-p2/straight-jump-p2/frame10-prefix-13/14の5行。inputs.json SHA9d8d8d92e7472b831de45bffbede5333b313fee22e07d4b7a237c65ac8c704e1、[1,8,9,9]固定batch1、policy136/value1。独立holdoutではない。

## 入場・実行・停止

07:05:46.088556UTCに173停止source SHA1a51ccf9248537a53cf873c6a25def1de05035c5f56d1abb519c22b82018b61f、全旧exact identity不在、現在science job不在を確認。現在選択processはscheduler/watchのみ、RSS合計164171776B、物理MemAvailable21020409856B。173のRAM4.5GiB/guard4GiB修正を現sourceで確認。監督owned=null、次予定07:13:14.296UTCでhard120+30秒を収容できた。GPU free10609MiB、compute ownerなし。物理12GiBを研究許可へ拡大していない。原173 WDLは読取0、強制停止/一時停止要求0。

GPUモデルjob開始07:05:46.088846UTC、終了07:05:48.415UTC、wall2.326347秒、exit0、guard停止0。manager PID3277697/starttick26408146、child3277775/26408453、bootab5e66ac-12ce-49b0-ac55-afe05e3f5216。両exact identityは検証時不在、childwait済/ownedremaining空。manager-stop.jsonのtracked/peakを保存。GPUjobは1回、各backend5 parity+warm1+steady8=14 forward、計42。科学成功反復0、training/game/newdeps/download/build0。

CPU0単1、Torch intra/inter1、ORT CPUExecutionProvider intra/inter1/SEQUENTIAL。Torch2.14.0+cu130/ORT1.30.0/RTX3060、float32/inference_mode/eval、AMP/TF32/cuDNN benchmark無効。peak child+manager RSS1220665344B（guard1879048192B以内）、Torch peakallocated21971456B/peakreserved35651584B（研究6GiB以内）。Torch allocator値はCUDA context/driver全量ではない。退出後nvidia-smiは入場前と同じused1500MiB/free10609MiB、compute ownerなし。元モデルhashと全source frozen hashの再確認成立。

## 数値と費用

判定は結果前固定abs1e-4+rtol1e-4、policy/valueの全要素を検査。保存出力のstdlib算術でNN0再集計し、shape/finite/value-rangeと記録maxabsを再確認した。丸め・救済・失敗入力補充0。旧CPU同backend bit一致とは別の有限数値主張。

| 比較 / 5入力の最大絶対差 | policy | value |
| --- | ---: | ---: |
| CPU ORT—Torch CPU | 3.874302e-6 | 6.854534e-7 |
| CPU ORT—Torch CUDA | 5.722046e-6 | 3.576279e-7 |
| Torch CPU—Torch CUDA | 4.351139e-6 | 1.043081e-6 |

| backend / 初期単入力 | warm1 ms | steady8中央値 ms | steady8範囲 ms |
| --- | ---: | ---: | ---: |
| CPU ORT | 4.488446 | 3.5707745 | 3.355101–4.026180 |
| Torch CPU | 7.974999 | 6.005743 | 5.750483–8.676075 |
| Torch CUDA | 2.686464 | 2.100652 | 1.942975–3.813368 |

全応答は毎要求の入力コピーから出力CPUコピー取得まで。CUDAはH2D・処理投入/forward・同期・D2Hを含む。CUDA steady系列の各段・全8値はresults.jsonに保持。初回parityのCUDA forward応答613.673741msを除外/隠蔽せず保存し、初期化/初回費として分ける。imports0.810255秒、ORT session0.023926秒、Torch CPU graph/weights0.043336秒、CUDA context/upload0.195152秒。warm1は5 parityの後に行った既warm状態であり冷初回ではない。

NN0 synthetic JSON stdio往復は同648入力、4113B要求/611B人工応答、startup17.619ms、warm1+steady8中央値0.0493885ms。これはPython pipeの人工0logits応答で、Rust実providerや実logit JSONの費用未測。実NN応答との単純加算を総native速度としない。batch8/多数selfplay利得、時計/棋力/NI/browser/Wasm/GPU正式対局/学習readyは未立証。約2msのforward主体であり多数小kernel・Python dispatch・IPCで利益が縮む反証を保持する。

## 次の判断：最大1案

新しい有限配分で、既native providerの実JSON/stdio経路へこのbatch1 adapterを接続し、保存initial要求のCPU ORT対CUDAでmodel/sessionを保持したwarm1+steady8の応答総費を比較する。担当experiment、私有provider/専用runの小scope、CPU1logical/RAM2GiB guard1.75/GPU6GiB、実行120秒以内/保持128KiBを提案。新依存・学習・arena・正式版変更は含めない。実輸送込み出力が同じ有限tolを満たし利益が残れば次の教師生成providerに採用候補、IPC支配/無差/悪化ならCPUを継続、数値失敗ならGPU教師へ採用せず最小原因を記録する。今回この案を自動開始しない。

## 再現・保存と受入れ

NN0: taskset -c 0 python3 -B tools/ai-sigma-gpu-inference/check_static.py。科学run入口はtaskset -c 0 python3 -B tools/ai-sigma-gpu-inference/launch.py、実child command/envはmanager-stop.jsonとlaunch.pyに記録。再現を記載しただけで新実行を許可せず、過去期限/同成功行は変更しない。結果SHAe22da8bb53116e866b857d54aa8825d15c72c90eb0ca9155221c2641cfa26e5a。preregister/source-binding/admission/results/verification/manager-stop/NN0-check/NN0-stdio/全waitattemptとGit保存を自域に保持。保存実量・小Git・forecastはstorage-final.json、必要Git byte復元とBeads backup/配送はhandoff.jsonへ。本人source/子停止済み、coordinator受入れ待ち。目標/他者issue close0。

停止済みrun記録はrun-records.tar.gzの各member（results.json/verification.json/admission.json/manager-stop.json等）を正本とし、archive-manifest.jsonで展開byte/hash一致を確認した。元の自己rawコピーは確認後だけ整理し、旧171/173等は削除0。inputs/preregister/source-binding/intake/Git-sourceは直接保持。再読込はtarから一時展開せずstreamでも可能。科学再実行には新配分と原参照入力が必要。
