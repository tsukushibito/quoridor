# SIGMA-WEBGPU-MEASURE / quoridor-4lc.115 / 契約1・現行枠8

coordinator→既experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746。ユーザーのGPU実測追加/研究継続を受けた実依頼。親枠8/common/experiment/実行記録規約を全文継承し、ready/show goal/self・pause/担当確認後115のみclaim、本人受領/開始を報告。同saved/model/effort/cwd、root114/92をclaimしない。

## 問いと経路
固定ONNXをCPU/Wasmと実WebGPUで実行したとき、単局面入出力・結果取得込みsteady費用と数値がどう違い、同探索で完成評価回数に寄与するか。モデル重み/sessionを保持し毎評価再転送しない。バッチ化/探索係数・FPU/order/tie/finish/caps変更を初手の前提にしない。
原112 tested3682ab7/113受入れを設計/既source参照として使い原write0。候補C1.5/fixedSigma、ONNX d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d/11663428B、immutableWasm1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01を共有参照。専用2Worker/SAB、browser main対局/合法/時計/結果、外Node起動監視回収終了後保存の採用責務を維持。初手対局0/holdout0/正式NI0、旧CPU/単WorkerWDLとGPU条件非混合。

## 単独writerと範囲
worktree /workspaces/quoridor/.worktree/ai-sigma。自己 tools/ai-sigma-webgpu-measure/、.artifacts/ai-sigma/resume-20261002/WEBGPU-MEASURE/、research-data/ai-sigma/115-webgpu-measure/、自己報告のみwrite。原112/113/共通source/モデル/registry/92運用/主製品read-only。必要に応じ現停止sourceを薄く参照・自己adapter、全copy/全履歴hash不要。局所Gitと新runで記録し普通debugは同予算内反復可能。

## 段階と事前計画
A: 現Chromium実WebGPU adapter/deviceと物理GPUを安価に確認する。既browserは--disable-gpu/--use-gl=disabled等を指定していたので、新自己browser profileのjob-local起動flagsとして必要差分を検討可（shared環境変更なし）。secure/crossOriginIsolated/SAB/依存loading、adapter情報/実compute sentinelと読戻し、GPUプロセス/driver/物理GPU観測を必要範囲で確認。/dev不在だけでGPU不在と断定しない。SwiftShader/llvmpipe等software adapterを実GPU性能へ格上げしない。adapter選択成功/RTX3060 host観測だけでモデルGPU実行と呼ばない。
B: 既ローカルORT-Web/対応WebGPU asset/operator可否・provider selection/fallbackとモデルを確認。同ONNX実GPUのdispatch/結果と物理GPU使用を裏付ける。operator一部CPU fallbackなら混合実行として割合/限界を明示し純GPU効果としない。外部GPU不明/VRAM監視不能で制限を守れない場合は実モデル測定を止め不足を報告。GPUdevice/session.close/destroy等必要解放はbrowser内、外owner回収は別記。
現在ローカルSIGMA-WEB-REFERENCEにはort.min.js/ort-wasm-simd-threaded.jsep.wasm/mjsがあるがwebgpu専用bundleは統括限定読取では見つからない。実API/既他cacheを確認し不足なら具体化する。主host/container/toolchain更新、共有依存/toolchain更新・モデル取得変更、実行時外部CDN、製品統合/push/公開、GPU学習は配分しない。既目標の必要な研究専用依存許可に基づき、既固定ORTと同じ版(現在ORT-Web1.21.0の実package/versionを照合)の公式WebGPU配布ファイルが不足する場合は、必要最小限を自己研究領域/既研究専用cacheへ取得可。公式配布元URL・exact版・package/integrity/取得hash/必要asset依存・保存先/byteを記録し既保存予算へ計上、実行はlocal assetを参照する。共有package/node_modules/toolchain/host/container変更・異版upgrade・モデル変更を含めない。取得前に必要版/assetを確認し、取得/展開の一時容量もguard内とする。正式primary docs等のreadonly確認は可。現環境不能なら成功化せず不足/最小追加条件/別案を速やか報告し、GPUだけに枠全てを費やさない。
C: 実GPU/固定モデル/制限確認が成立した範囲で、同3golden(initial-p1/asym-hv-p2/straight-jump-p2)、648floatfeatures/137NN/Actionprior固定mixedabs1e-4+rtol1e-4/finite/strictvalue[-1,1]をCPU基準と照合。最大差/失敗/モデル演算差を保持し不成立を性能負例にしない。初期化・weights配置/compile・warmup・steadyを別時計。CPU/Wasm基準とWebGPUを同profile・同入力/同出力CPU読戻し境界、session保持・各contextwarm2/steady8を出発計画(合計60呼出)として結果前にconfig固定、AB/BAを交互にする。startupや別数値gate推論は別分母、全warm/steady/未実施を保存し有利行選別0。API await/queue completion/読戻しを内核命令時刻としない。中央値/minmax/ばらつき/転送/投入/読戻しの可能spanを報告。成立不足なら結果を見る前に必要最小に計画変更し理由/版を保存。
D: 数値と停止/公開基本条件が成立後のみ、同candidate検索のbackend因子をCPU/Wasm↔WebGPUへ変更し、同C1.5/seed1979/order/finish/caps/history・T500/cutoff402/adopt411の完成評価/NNcalls/深さ/初回有効CP/公開時刻と残GPU回収を比較。3context×2backend×2反復を出発上限12検索として結果前固定、対局開始0。実装の同経路bindが成立しなければ単局面測定のみで未実施を報告。完成評価countと単NN費用を別問いに保ち、速度から棋力/正式NIを認定しない。専用Worker次自手旧回収、相手t0旧ACK非依存、確定後旧返却discardを維持し先読み/2Worker常時探索0。

## 予算と期限
親CPU4/RAM8/保持+未使用予約12GiB、GPU VRAM6GiB上限/各job30分以内を維持し学習累積2hとは分ける。配分: browser全process/GPUprocess/2sessionsをRAM6GiB/currentRSSguard5.5GiB、CPUaffinity[2]・推論CPU各1thread、重job直列。stewardRAM1/CPU0、軽い統括管理と合計内、モデル同居メモリ帰属を勝手に分割しない。研究GPUdevice/session allocationと物理VRAM観測を保存、上限guard5.5GiBを目安に制限。全GPU使用が不明なら保守的に総量をguardし不足/不可を区別。RAM計測がGPU専用VRAMを含むとは扱わない。
既experiment entry内の未使用配分を実確認して新runtime128MiB/guard112MiBを利用（追加予約0）。必要Git/archive/専用TMPも計上、確認済未使用だけ返却/再配分し古いpeakを現在量に加算しない。モデル/共有依存run全copy0。
各browserjob600秒(30分上限より短い)、全heavy1800秒。安いsource/mockのみCPU0/RAM1guard896・各60秒/累計180秒、browser NN0でもRAM6guard5.5。GPU他重job/GPU未知owner競合時は開始しない。管理CPU/PID/boot/starttick/PPID・currentRSS/VRAM/timeout/回収を記録。device loss/guard/ユーザーpause/所有不明/期限で該当jobを止める。容量systemError再発は状態と引渡しを残し盲目再起動/設定変更0。
受領から処理60分/新run55分/提出70分と絶対処理11:30/新run11:25/提出11:40UTCの早い方。起動preflight可否・不足は待たず途中報告。親14:05:49新重job停止/14:10:49監督/14:13:49monitor/14:15:49終了を迂回しない。旧個別枠期限を延長せず新115/newrunで区別。

## 受入れ/引渡し
実GPU可否→数値/費用→実completed評価への影響の各支持/不支持/不成立/未実施を有限裁定。モデル初期化/準備成功を性能向上とせず全失敗/未実施保持。物理GPU不成立なら不足報告を受入れられるがGPU性能成功とはしない。source/runtime/device/Model/search/timer/monitor回収→本文前停止・必要hashafter→Git/archive必要復元→Beadsnotes/backup→coordinatorへ。現在identity不在を自然終了/全期間保証へ格上げしない。重大性能主張の必要範囲独立確認は統括が停止最小版から配分し、新全史/一run一issue/単発窓gateを作らない。goal/他者close0、受入れ担当coordinator。
