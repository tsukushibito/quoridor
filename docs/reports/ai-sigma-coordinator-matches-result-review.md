# 固定32局の受領と次の判別実験

quoridor-4lc coordinator / 2026-10-01 UTC。目標契約版2、全体終了04:00 UTC /13:00 JSTを継承。旧run処理00:45/提出01:00と事前比較条件は変更しない。

SIGMA-P32-V2-R3-01は予定32局/各platform8先後pair完遂。統括はimmutable results-tableから独立算術しnative-local9勝0分7敗/score.5625/L.129795、browser3勝0分13敗/score.1875/L0を再計算した。native-localはRust-native対固定Sigma-WebローカルCPU、C++比較ではない。原報告SHA5fb3486d…c592、入力実hashと算術はdispatch/matches-result-next-inputs.json。全棋譜再審判/応答照合はcritic .25へ渡す。探索的小標本・非劣性未立証・目標未達を保持。browser2期限loss(527.097/502.310ms)は分母へ残しinvalid救済0。

観測NN中央値Rust-native4.239ms/Rust-Wasm47.5ms/参照ORT13ms・完成sim66/9/22からブラウザの分離ORT案Bに判別費用を配分する。共通Rust同期tract案AとB0案Cを保持し速度差を棋力差の確定原因にしない。experiment .26は同じRust探索のpending leaf/resumeとORT-Web1.21単CPU評価を研究だけで試作し、PUCT/FPU/model/rules/caps/tieを同時変更しない。正しさ・世代・取消・error・28数値・通常不変gate後に固定golden小同時計診断。新対局はこの契約に含めず、追加実験は別事前登録と独立gate後。旧32局/m/score/条件は結果後変更0。

新配分: critic .25 CPU0/RAM1GiB/new128MiB/処理00:35提出00:45、experiment .26準備CPU2,4/jobs2・診断CPU2単1/RAM4GiB/new1.5GiB/所有5GiB/処理01:35提出01:45、GPU/学習0、root含め3役。exp現保守保存3,676,045,312B、hyp上限約2.383GB、model約12MB/critic実物を含め新規12GiB内、CPU4/RAM8以内。既存固定runtime/cache読取再利用。過去期限/RSS/TMP/affinity逸脱・tail/無競合/深部overlay/実arena/200手/no-legal/entropy/fullfingerprint/配布未確認は保持、延長による遡及適合0。

成績限定受入れはcritic .25報告待ち。.21本人closeは独立受入れ後、goal未達のため継続。契約2件と実send受領はdispatch/matches-result-next.jsonへ。報告待ちはcritic .25 / experiment .26 → coordinator。統括算術初回はnative platform表記の誤指定でZeroDivisionError、実native-localへ訂正し再計算、原write0/失敗はinput JSONへ保持。
