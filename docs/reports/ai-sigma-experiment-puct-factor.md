# SIGMA-PUCT-FACTOR / .34 / 試行1 / 契約版1
experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親契約版2/04:00、旧逸脱保持。

C1.5→1.0のみ新copyに変更。元.26 immutable Wasmを対照、新候補8438310c…d9dd、同ORT1.21.0/モデル/RuleA/Q0/seed1979/order/tie/finish保持。20合法golden、8/32sim、512nodes/depth24/step1、診断T1e9。結果前preregister SHA bbe1dfc6209a5ee3f01a4fa2f5d8cd51038dc68f26d8ef039a9039211e8700bb、全80検索/40比較組を実施。kernel.patchは定数1行のみ、lib/research/lock完全同一。元controlをrebuildせず元binaryそのもので比較。旧96入力と22sourceの現在hash不変。

着手変更3/40、訪問分布変更20/40。8simは1/20・7/20、32simは2/20・13/20。変更はstraight-jump-p2/32:31→131(L1=14)、behind-wall-diagonal-p2/8:123→181(L1=4)、one-wall-in-hand/32:5→13(L1=16)。全40組のnodes/depth/NN/cap/tie/shared入力はcomparison.json。shared NN入力の最大差0。Cは有限固定入力で探索経路を変えるが、改善方向・H2全体・棋力・速度因果は未確定。

固定rootの648f32bits×40、NN137×40=5480要素、prior4634要素は事前混合gate失敗0、NN最大差5.49e-6。root features/logits/priorは両C厳密同一。State/std-only checkerで1452node context/1372合法遷移/4382選択(score→seed)・backup符号f32bits・finish(visits→prior→seed)を再構成、失敗0。root node.visitsを直接取得し正常sim一致/edge和sim−1、終端4検索NN0。cap/fallback0。旧.28の別分母数値は流用していない。

初回Content-TypeでNN前失敗、修正1回後完了。独立checker初回はhistory関数scope誤り、原因修正1回後保存rawのみ検査。両失敗log/source保持、NN条件・入力・閾値変更0。offline buildが旧Cargo .global-cacheアクセス管理DB57344bytesを更新した読取限定逸脱を保持（before hash欠測）、副次保存へ全量加算。新取得0。製品/rootlock/モデル/旧証拠の変更0。

NN終了03:13:35、全自己job終了03:15:09、03:16:15のstopJSONで39 PID/starttick identity不在。全runtime TID CPU2、補正0。準備2,4/jobs2、peak RSS2769104896bytes、unique保存約34.4MB含副次/所有保守約3.816GB、guard内。ORT実allocator/物理共有RSS・正式無競合は未確認。新native/通常suite/時計安全/対局/採用0。sourcewrite停止03:17:27、独立受入れ待ちin_progress。.30は限定理由と全未確認を残して本人close、.32/.33 no-go保持。

詳細 .artifacts/ai-sigma/runs/SIGMA-PUCT-FACTOR/manifest-final.json、全row/NN/backup/stats、job-source/log/processを保持。再現は新出力に隔離しrunner build→factor-browser→check-raw、既run不変・期限内のみ。独立受入れ待ち、目標未達。
