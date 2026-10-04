凍結NNUEとtrain-fit距離Dを同じrootbest-first αβと100ms受信予算で対戦させた探索的診断は、NNUE側2勝5敗・1UNKNOWN（全8予定、4opening色交換）だった。slot1は100.722574msで親受信期限を越えたためActionを採用せず、敗北へ変換しない。7局は保存prefixの全合法RuleA再生と終局winnerを本人NN0検算した。4pair・単runversion群なのでNI、Sigma同等、最高棋力を認定しない。

goal quoridor-4lc / issue quoridor-4lc.236、frame19 2026-10-04T22:52:46Z–2026-10-05T00:52:46Z。Node-hostedでありRust/Wasm/Sigma実装の棋力を代弁しない。freezeSHA2bac8f1f7ad87b83ac0549c01bb32eb0c8d0a2f39a05c717420e20cd668e6a60、12193LEf32/48772B tensorSHA b81792d5ba00c6d79b58cada2fc81d84ea822db48c04420b4e269fb9b71841b3、scale68f8b43a・actualSTM標準化/recomp0を維持。D係数a=.06038215201109912,b=7.925687690687516、同f32clip。旧229最終curve/test/bootstrap independent NOT_RUNを保持し、開封旧testを選定へ読み戻していない。

全合法・TT0/noise0/policy除外0、clone-parent/history保持。前完成depthのrootbestだけを先頭に移し残Action昇順stable、strict-greater tie。depth1未完はNO_COMPLETED_DEPTH、未完depthのvalue/PVをdiscard。非best failsoftはbounds、全exact child値/等値argmax集合はNOT_RECORDED。rootmean蒸留評価はminimax leaf真値ではなく、historyをNN入力へ追加していない。

| slot | opening ply | NNUE side | status | NNUE結果 | 最終ply | 応答手数 |
|---|---:|---:|---|---|---:|---:|
| 1 | 0 | 1 | UNKNOWN | UNKNOWN | 4 | 5 |
| 2 | 0 | 2 | TERMINAL | L | 113 | 113 |
| 3 | 8 | 1 | TERMINAL | L | 66 | 58 |
| 4 | 8 | 2 | TERMINAL | L | 15 | 7 |
| 5 | 12 | 1 | TERMINAL | L | 44 | 32 |
| 6 | 12 | 2 | TERMINAL | W | 50 | 38 |
| 7 | 20 | 1 | TERMINAL | L | 42 | 22 |
| 8 | 20 | 2 | TERMINAL | W | 42 | 22 |

pilot first4→later4は時計機構がlateを拒否でき、共有harness故障が未観測、資源と残予算が成立したため進めた。WDLで後半を選別していない。全8の分母と旧失敗attemptを保持する。

100msは入力供給可能t0から親がresponse全parse・generation/key/history照合・合法completed Action確認を完了したmonotonic t1まで。内部90ms、配送margin10ms。合法生成を含む高費APIの開始前/終了後とnode境界で協調時計確認し、outer100msを独立判定。timer callbackだけを期限証明にしない。旧世代、late、EOF、未完depth、parse検査overshootの6fixtureが不採用PASS。初版timer早期wake98.536msを結果保持し、新版では100msまで残待機。late応答のstop/drainではdiscardのみ記録する新ログ版を後半に使用、時計/探索条件は同じ。

本対局297hand: pilot182受信+1outer期限、later114受信。受信Actionは全てt1-t0<=100ms。pilot中央値90.570ms/max100.723ms、later中央値90.524ms/max95.996ms。旧guardcensor45handも保存し採用Actionの合法/時計確認PASS。親/childは同CPU2にaffinity継承、実GPU0、各jobfamily guard1.75GiB。起動load/cold/停止回収はwholejob費で保存しhand無条件無課金にはしない。

固定4root×同評価器NNUE/D×Action昇順/rootbest-first×固定順2反復（32search）はnode4096/requestdepth1→3。初期NNUE完成depthは昇順1/1に対しrootbest-first2/2、Action148は同じだが完成深さの仕事が異なる。他3rootは双方depth2、同depth root値有限tol内・Action一致。時間差は反復で揺れ、cache/JIT/固定順/浮動小数/枝刈り/完成仕事量の交絡を残す。これは一般速度利益や同時間棋力の証明ではない。

| received engine profile（旧censor含む） | NNUE | D |
|---|---:|---:|
| received hands | 171 | 171 |
| processed nodes | 291729 | 411487 |
| model NN / D eval | 209276 | 287719 |

terminal_inclusive_ms: NNUE 4241.047ms / D 5146.193ms。
legal_order_inclusive_ms: NNUE 1414.361ms / D 2035.033ms。
clone_ms: NNUE 2307.625ms / D 3218.850ms。
input_full_delta_inclusive_ms: NNUE 4345.912ms / D 0.000ms。
evaluator_inclusive_ms: NNUE 1775.687ms / D 3492.855ms。
control_ms: NNUE 355.678ms / D 402.270ms。

これらはoverlapping inclusive spanであり排他的支配費へ合算しない。RuleA terminalは合法生成cacheを含み、D evaluatorもterminal/input処理を含む。NNUEのinput/full-delta spanもmaps/features/copyを含む。異なる探索枝/深さ/terminal数なので分離した唯一の費原因は未認定。

失敗版pilot-r1は23:10:51.966714→23:10:56.240881、4.274171s、45hand途中でguardianがgit hash-objectへの.py入力を科学scriptと誤認し自己停止。原FOREIGN_COMPUTE_STARTED/PID391813tick40846374/ppid391801/argv/processを保持する。D状態はIO点観測で全性能無競合の認定ではない。新guardは実argv executableがPython/Nodeであることを先確認しGit入力を科学扱いしない。旧slot1UNKNOWNとslots2..4NOT_STARTEDを別旧版ledgerに残し、pilot-r2による成功置換をしない。旧既知NN23242/inflightNN UNKNOWN、最大1hand8192を保守加算。

全attempt科学guardianwall 40.254773s、既知NN 270156、保守charge 278348（cap4000000）、全科学cap1200s内。peakfamilyRSS 315637760B<1.75GiB、CPU2単1/GPU0。背景commandwholewall合計53.843702sは科学wallと重複し加算しない。prefix NN0と保存検算を別費、source著述/通信/LLM待機/全elapsed exact aggregateはUNKNOWNとし0へ補完しない。64MiB予約/56MiBguard、新scopeactualとGit/temp/finalmetadataをfinal-cost-storage-v1.jsonで記録、旧unknown減額0/親追加0。

科学source12と全子wait/PIDtick不在はscience-stop-v1.json、全slotと旧費はall-attempt-result-v1.json、時計・depth・値照合・合法prefixはsaved-verification-v1.json。主archive/memberSHA/Git byte復元とBeadsbackupを保存する。独立238の算術受入れは別であり、この本人検算を独立PASSにしない。

次最大1案は、同RuleA/全合法・同凍結評価器を維持しterminal/拒否nodeの前に不要なQF1 accumulatorを作らない薄い遅延接続の固定仕事比較。現input/full-delta inclusive spanは改善動機に留め、全額回収を仮定しない。必要costはsource差分と固定root/full-delta有限parity・同work短測定、見込1短CPUjob、別配分でのみ実行。改善が小さければ中止し、同時間棋力に戻す。terminal/legal protectedcache方式237は大幅負費のため不採用、第一8へmergeなし。NNUE value自体の弱さ、葉評価/履歴/分布と探索量差の競合説明は残す。新train/test/teacher/TT/policy/追加gameは自動開始しない。
