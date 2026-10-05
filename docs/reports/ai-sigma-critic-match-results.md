# SIGMA-MATCH-RESULTS-CRITIC / 試行1 / 契約版1
quoridor-4lc.25、critic 01a0f31d-8227-7e03-a7e6-915b4918c11b。目標契約版2（04:00UTC）継承。判定: 固定32局の探索的成績を限定支持。目標未達・正式非劣性未立証。統括受入れ待ち。

実施: revision3の固定game.js/context/judgeを同bytesで自己copyし、独立コードで全prefix、1534応答とjudge記録、1532採用手、30goal終局、2候補lossを再判定。合法集合・壁reachability・jump/P2の209対応・反復history・終端優先を逐手再生し、終局後継続なし。生のID/generation/engine/prefix/seed/T500g91/t0・配送stamp・fallbackを別軸で照合。table/results/checkpoint/16pairも一致。

結果: native-local（Rust-native対固定Sigma-Web）9W0D7L、score .5625、m8、L .12979540434942866。browser 3W0D13L、score .1875、m8、L0。XiとL=max(0,meanXi−sqrt(log20/16))を独立再計算。32局を独立標本32として扱わない。両下限≤.45、達成認定不可。

参照768/768、native371/371、Wasm393/395採用。game3はNO_RESPONSE_TIMEOUT 527.096867ms、公開Actionなし・stale拒否、遅着timeoutもdiscard/cleanup済み。game5は502.309811msの合法checkpoint32をlate拒否。両方候補負け、invalidpair/globalretry0。restartは初回起動を除き1回、session2へ移行し旧PID0→load/warm/reclock、別log保存を照合。

結果前v2/freeze、8unique開始履歴/platform、同prefix先後交換、seed1979、固定抽出・順序を再生成し一致。12ping×4時計×2sessionのoffset区間と全要求の早側換算を再計算。secret値はログ化0。76入力実hash前後不変、manifest28checks一致。.26 live実装は不使用。入力完全SHA/自己script/hash/patch/commandは verification/CRITIC-MATCH-RESULTS/{input-before,input-after,copy-patches,summary}.json とstageへ保存。

探索的診断: elapsed中央値 native416.071/reference424.271/Wasm450.537ms。NN呼出数中央値65/22/9、NN単call時間4.239/13/47.5ms（分母23816/15924/3337）。欠測1を0に補完せず、simとNNを区別。native4096sim到達9要求、cap=true0。NN速度による勝敗因果は未確定。

自己検証の初回2失敗は、拒否watchdogのstaleとnative generation階層についてcritic側assertの誤り。原rawを変更せずschemaに合わせ修正し、失敗source/logを保持。最終replay/audit/抽出/evidenceはexit0。CPU0全観測TID、RSS観測658632704B、追加約0.21MiB、NN/build/取得/追加game/GPU0。00:27:17最終child終了、00:27:42.448633にruntime-stopped.jsonを先保存、追跡PID0、port0/temp残0。他者kill0。処理00:35/新job00:32より前に停止。

未確認: 時計tail・瞬間RSS・外部競合、完全manifest来歴連鎖、未知training overlap、真に合法200手/no-legal到達、深部探索一般安全性、C++成績/製品採用。有限観測をT/g保証にしない。過去の期限/RSS/TMP/affinity逸脱と旧negativeは遡及適合しない。今回の成績再構成は支持、追加実験は別契約・結果前固定を要する。
