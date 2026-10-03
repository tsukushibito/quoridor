# CPU並列校正：60要求保存、正式資源条件は未成立

固定initial-p1の60予定要求を60全て保存し、全てcompleted_legalだった。648特徴、state/historyと137 NN出力のf32 bitsは保存151 r2の同入力と一致した。手NN909、session startup60は別分母。これは孤立検索の校正であり、WDL/NI標本ではない。formal_ready=false。

契約cd4aa344、受領03:06:15.627920。CPU core2/4/6/8のsolo→2arena→4arena、各arena C,R,R,C,C,R（各engine warm1/steady2）を結果前固定した。各arenaに専用2Worker/session/SAB、ORT1.21 CPU各1thread、T500/cut402/adopt411/seed1979、immutable faithful binary50018179…3f2c2を保持。10arena/20session。毎要求fresh tree、両旧zero後の同入力孤立検索なので、通常対局の相手t0と旧NN重複を検証したとは言わない。

| mode / CPU | 実開始/予定 | 重wall秒（init/debug/回収込み） | aggregate RSS peak bytes | exit |
|---|---:|---:|---:|---:|
| solo2 / [2] | 6/6 | 99.768139 | 1771790336 | -15 |
| solo4 / [4] | 6/6 | 16.776084 | 1774837760 | 0 |
| solo6 / [6] | 6/6 | 18.359364 | 1825734656 | 0 |
| solo8 / [8] | 6/6 | 19.428907 | 1814290432 | 0 |
| mode2 / [2, 4] | 12/12 | 25.839078 | 3187142656 | 0 |
| mode4 / [2, 4, 6, 8] | 24/24 | 38.017619 | 6096449536 | 0 |

重累計218.189191秒/360、各job180秒以下。4modeは6,096,449,536 bytes < guard6.5GiB（契約7GiB）、研究8GiB内の直前admissionを保存した。CPUは物理別core、各観測TIDのpool外affinity違反0。guardian/parentもpool先頭coreへ含め、92affinityは変更していない。158/160短CPU0と外heavy/currentRAMを各mode前に確認し、LLM active数はgateにしていない。RSSは40ms標本で瞬間peak保証ではなく、arena別aggregate current系列は欠測。各PID初観測RSS/maxRSSは原processに保持。

solo2は科学6行保存後、inner登録ROOT_MISMATCHによるcleanup失敗が発生した。本人guardianのexact identity/ownershipを確認し自己回収、exit-15/outer remaining・unknown空。原失敗/管理停止要求/モデルdrop/timer receiptを保持し、成功科学行は再実行していない。私有arena ledgerをouter sole-rootへ正確にbindする修復後の未開始5jobはexit0。科学成功とcontrol成功を分け、全job自然終了とはしない。

科学実sourceはsolo2 be872e8、以後a3094fd、事前登録564593e。source-before-runは初期記録であり、実served source/hashは各runのinputs/actual-served-source/source-bindingsが正本。policy/kernel/model/buildの変更0。collect.pyは保存算術のみ。同sourceのNN0 K32 saved tape replayとrouting/control/pause/error→spawn0 mockをAI前に実施した。

参考steady batch wall係数は2mode1.980531、4mode3.814258。これはcore対応solo spanの和/並列spanで、phase barrier・ACK・要求間処理を含む。初期化/保存/回収の費用を別表に残し、対局速度や同CPU証明へ換算しない。

| 並列mode/core | API await比（並列/同core solo） | 採用backup比 |
|---|---:|---:|
| mode2/2 | 0.973488 | 0.957447 |
| mode2/4 | 0.464628 | 1.911111 |
| mode4/2 | 1.240338 | 0.808511 |
| mode4/4 | 0.490594 | 1.844444 |
| mode4/6 | 0.500016 | 1.886364 |
| mode4/8 | 0.478273 | 1.886364 |

core2とoff-anchorの変化は逆方向で、両engineが同程度に遅化したとも言えない。engine別steady全行をcost-and-limitations.jsonに保存。soloは管理とarenaが同core、並列は管理がcore2に偏る構成だった。これが差の原因という推測は未検証で、host負荷/周波数/熱/順序も切り分けていない。既1core成績へ並列条件を遡及適用しない。

公開elapsedは410.360108〜415.395020msでnominal500内、後返却discard28、確定後新API開始を観測した数0。firstCPはpublication begin/validation endとWorker-main clock校正を用いた区間であり、Atomicstore実時刻は欠測。採用CP/NN/completed、terminal-noNN（候補直接counter、参照差分導出）、first/later API、selfwait/ACK/旧返却、phase release/t0 skewを60行それぞれ保持。API awaitはkernelCPUではない。cross-browser epoch同期誤差を独立にboundしたとも言わない。

最大1次案は正式比較のCPU-provider/残NN課金修復。Worker TIDと残処理区間CPUを原因側へbindし、normal相手t0を旧ACK前提にせず、管理処理を選定pool内で対称に配分又は明示会計する。その記録で同実効budgetを支持できるまでformal_ready=false。mode2/4は物理実行可能の有限支持のみで、正式採用modeはcoordinator/158の結果前固定に委ねる。今回追加WDL/NN/NNUE実装を開始しない。

最終heavy03:19:55.971795終了。science-stop.json記録時の同boot570 exact identityは全て現在不在、全outer remaining/unknown空。main timer、モデルdrop、Worker/SAB、監視callback、inner controlled/forced、outerwaitを原receiptで分離した。現在不在は全期間/全host/自然終了保証ではない。科学source停止後のpack/Git/Beads helperは別。

再現はpreregister、6config、runner/program/arena/browser private source、実run source binding、原151 readonly binary/model/依存bindingから行う。新依存/build/重み取得0。未Git依存をGitだけで再構成できるとはしない。全科学成功の再実行/置換0。static準備と保存helperの全wall/全team費は未集計であり0に補完しない。
