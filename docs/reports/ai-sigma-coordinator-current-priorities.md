# 現在の優先順位と評価・学習計画

2026-10-03版11。ユーザー確定方針により、棋力検証・大量対局・自己対局の主環境をネイティブとし、高速化・効率化で結果と学習データを得る総費を下げる。最終目標はNNUE型の最高棋力、初期Sigma同等は未認定。Wasmは必要な数値/探索/合法/応答/取消と少数の実用確認に限定し、大規模Wasm NIを主研究の入口にしない。CPU/GPUは目的と実費から選び、GPU利用を開始条件にしない。

開始00:15:21UTC維持、明示4時間追加で終了08:15:21UTC、重開始08:05:21/監督08:10:21/monitor08:13:21。CPU4logical/RAM8GiB/保持＋予約12GiB、既GPU推論6GiB/job30min・追加GPU学習0。親期限と92運用はsteward単独writerで更新済み、同schedulerを重複開始しない。旧枠の個別期限/結果は変えない。

| 優先 | 問い・到達点 | 配分と完了条件 | 次判断 |
| --- | --- | --- | --- |
| 主1 | 最小native忠実Sigma基準と同時間対局が動くか、総費はいくらか | 165既experiment。151 Rust探索＋固定Web751186のnative-hosted参照＋同ONNX/既CPU provider、私有build→5入力sameK32→条件付き新8pair16診断。build120s/機構180s/対局1800s、新64MiB既枠内 | 同K有限対応とsamewall費/結果を分けて受入れ、native正式設計・教師生成へ。障害なら最小route修復。formal1200/Wasm再検証の義務0 |
| 並行小調査 | CPU/native輸送と既GPU providerの実行可能性/費用の選択 | 164既hypothesis。新NN/GPU/学習0、静的60s/128KiB、10分速報。既依存とsourceから最大1経路 | CPU first優先。GPUは必要な単局面/batch実測を後続配分、GPU対応を文字列だけで認定0 |
| 必要独立視点 | native参照・時計・局面/標本が主問いを満たすか | 166既critic。静的90s/新2MiB、10分速報。実装開始gate0 | 重大scope差を結果前修正、少数診断をNIにしない。正式比較の新native条件を後続固定 |
| 学習準備 | 実対局π/z/rootmean→lineage group→本PV学習→独立arena | 162で小CPU toy 20step/weights-only checkpoint/ONNX5行parityが実成立。現在は5診断の4train/1validationのみ | native基準のπ/z出力を小schemaへ接続する次配分。full selfplay/学習規模/実PV構造/独立holdout未整備、GPU学習追加0 |
| NNUE/方策 | 前段の基準・教師・費用からNNUE＋αβ/方策順序を選ぶ | 156予備コスト終了、主NNUE実装拡大0。方策head候補は正本登録済み | 総探索費と棋力を比較できる段階で別配分、toy損失やcache速度を棋力へ置換0 |

同等の実用定義は5pp非劣性/片側95%という旧158案を保存し、browser m600/1200gameや旧rawを遡及変更しない。旧式L=max(0,mean−sqrt(log20/(2m)))>.45、m600でmean.5を通すが高power保証はない（例示Bernoulli pair power約.51628、分布自由95%power十分m2397）。計画成立、実測不足保留、非劣性支持、劣性支持、不確かを区別する。新native版の参照・モデル/backend・時計/資源・独立開始分布/抽出仮定・fault全分母・固定m/停止を正式データ前に別固定し、今回16診断や教師へ正式holdoutを流用しない。native結果をbrowser NI達成へ読み替えない。

161 NN0 clock14mock、163 browser fixed1000ms/12要求のD500までACKとmain402採用を有限受入れ。163preregisterに1000cycleがあり、161『ACKは次1000前で可』との差は『D500まで必須』として保存、prototype14mockをD500実証へ転用しない。kernelCPU/TID/cutoff誤差等欠測を残しformal_ready=false。費用の大きいbrowser正式clock全保証へ自動連鎖せず、この基準を主native経路へ移す。151/153/155の機構/合法16局7勝9敗を再利用するが同等未立証。

監督の『fixture負担除去を実探索/棋力改善としない』『全cacheの優劣を4状態結果で決めない』『軽い学習準備と正式評価を分ける』を採用。次効果確認はnative機構成立の有無・games/sec/有効教師行/sec・起動/NN/輸送/記録の支配費と実際の配分変更。主基盤の巨大化/追加承認層を効果と数えない。前のbrowser主計画はresearch-data/ai-sigma/frame10-coordinator-start/priorities-before-native-20261003.mdに保存。

04:37–04:38UTC：165本人04:37:21.307017受領/claim私有静的開始、既nativeCPU ORT1.30.0を両engineで使う（browser1.21とは別）。164本人04:38:34.800333受領/claim静的開始、166本人04:38:32受領/04:38:55claim静的開始を確認。166独立速報のevent-driven共通quiescence→新actualt0方式を採用候補として165へactive補足配送。特徴/NN/pipeABI/受信検証を500msへ同ruleで含める定義と原因側cleanup費を事前固定、1000msbrowser周期義務0。推定kernelCPUや完全公平性へ格上げしない。rootへ実配分/開始と必要設計3path writer案を実報告受理04:40:08、本文反映待ちは研究開始gate0。

04:44UTC結果前補足：166が参照だけのbrowser用simulation setTimeout費と異種clock epoch仮定を独立発見。private native wrapperの共通制御/yield/実輸送とcontroller単一monotonicでのt0/受信採用/publicを結果前固定するよう165へ採用補足配送（原policy変更0、除去自体を棋力改善にしない）。164の常駐CPU-first経路を支持、既ORT metadataはAzure/CPUのみでCUDA/TensorRT未対応、原ONNX固定batch1を8件要求と真batch8で区別。GPU新配分0。root167設計3doc Gitdb9a03bfをmain/mirror/current最小照合しnative主方針を継承、roles/common/registryrefresh不要。実source反映/科学成立の確認は165報告、採否の効果は次自然監督で追う。

164最終0fcfc6e6を必要8Gitblob/current・source2hash/同期子waitと照合し有限受入れ。常駐nativeRustJSONL/WebJS/同PythonORT1.30CPU第一経路を採用。codec中央値0.055281msはIPC/NN/sessionを含まず実経路速度未測定、CPU metadata Azure/CPUのみと固定ONNX batch1/GPU実行未確認を保持。165の主機構・条件付き少数対局と166独立scope最終をcoordinatorへの報告待ちとして継続、hypothesisへ調査のみの自動連鎖/新NN/GPU実行を追加しない。

166最終12b20c7f/handofff4131b29を必要12＋3Gitblob/current/静的停止/backupで有限受入れ。独立指摘が04:49:44snapshotのnative loop人工timer除去/Python epoch分離へ反映した限定根拠を支持し、165の実NN・controller採用・quiescenceは未確認のまま。共通500ms内の特徴/NN/輸送/検証と原因側cleanup、startup別を採用。未測kernelCPU同値を主張しないが、同資源samewallは同じ許可core/thread/時間条件で実装効率も比較する問いであり、消費CPU cycleの厳密等値/全TID証明を新一律入口にしない。正式版/抽出/clock/fault/固定mの事前条件は維持。新native費は165から更新、旧53.5625手×500msによる1200局8h55m37.5は費用例だけでinit/cleanup/save/並列負荷別。現在主165の実装・機構/条件付き少数対局報告待ち、全role稼働維持/新scope調査自動連鎖は不要。

165 StageA native sourcea09279c/rawdee3d3b5…の固定5×両K32/NN320＋startup2で離散・ledger差なしを本人速報、rawSHA/owner集計/phase停止を最小照合して条件付き16準備継続を支持。全165書込停止やsameCPU/棋力成立とは別。quoridor-4lc.168既criticへ保存NN0の独立算術をCPU0/RAM1guard896/static180/new8MiBで配分、NN/game/build0、StageB受入れ待ちgate0。native同providerの機構claimへ必要範囲の確認で、全deep/全史再監査に拡大しない。

168data1b572e17/handoff013364d0の24+3必要Gitblob/current・source/静的子停止・backupを照合し有限受入れ。native sourcea09279c/binary166dd0c4の固定10K32、独立保存算術で320CP/320NN、1450select/1770祖先update、特徴/NNbits/path/訪問/Action/ledger一致を支持。f64微差は別、raw/backend再実行0/sharedRuleA等限界あり。これでnative機構基準を有限支持し、全game/同wall/棋力NIは165結果で別評価。StageB変更engineをStageA測定版へ付替え0。主165契約の登録16/費用/教師schemaをcoordinator報告待ちとして継続し、checker追加/時計完全保証を入口に積み増さない。

05:27節目: 165固定native16は本人W6D0L10/NN40378/startup16/public898で科学停止。全16raw終局GOAL/score6と停止SHA/outeremptyを最低限照合、棋力同等/NIは未認定。残る165費用集計・openingπ/z小export・必要保存を維持し、新quoridor-4lc.169既criticへCPU0/static180/RAM1guard896/new2MiBの全棋譜/clock/分母独立保存裁定を配分。次主仕事はnative実費と有効教師/secを根拠に最小効率変更または独立評価へ選ぶ。方針/標本/旧成績の救済変更0。

05:35運用: supervisor1a9d886cの32MiB/forecast拒否と重複wrapper全notes保存削減案を採用、既92単独stewardへ新run bounded記録/根拠付きforecast修復。現実量未計量はunknown、歴史raw保持・容量追加/親減額0。次自然ownedobserve/finish成立と保存実増分を効果点検、165/169研究gate0。
165参照terminal-only loopがIPCcancelを処理できず約10秒cleanupとなった具体不足を本人早報、科学後NN0の両engine共通event-drain修復を既デバッグ枠内で採用。元16/政策/時計/raw成功は再実行救済0、next control版を分離し総費改善を確認する。

169独立速報は898合法手/全16goal/W6D0L10/mean.375を支持。実admit記録が合法検査/clone/cache完了前のため402完了は未確認、違反の確定でも元勝敗救済でもない。terminal同期loop取消不足＋stamp順の修復を165既debugのNN0/static120合計で採用、元16/旧science-stopは保存、新controlsource/modeを分離。169有限最終まで新NN0連鎖を増やさず、元165cost/export/packと92bounded-record復旧を待つ。92本人受領/pause所有確認/現在修復実開始を報告で確認、自然tick効果は未着。

05:45節目: 165 NN0control修復a78停止SHAb5d9b87d15cd93c4da198a3ee518c41de727acc867806857c653549160efb7c8のsource/model0/outeremptyをminimum照合し、tape対応と人工取消改善は有限本人根拠として保持、実ORT/新samewall未確認。新quoridor-4lc.170同experimentへ原165最小pack/停止引渡し後の2input8solo＋条件付き4arena32要求を最大heavy120秒/新8MiB既枠内で配分。実採用完了/取消zero/単clock/providerとparallel費を一度測り、native評価・教師生成版/mode/実費を選ぶ。NI/WDL/学習の追加配分ではなく、既修復を実推論で有限確認。169全文/92修復受入れgate0、CPU0実job競合時parallel延期/不足明示。次主仕事はその費用で正式native計画又は最小教師生成へ、単なるruntime確認の連鎖を続けない。

169最終dataa835ef3c/handoffdd922324の必要23+2current/Git/source子停止backupを照合し有限受入れclose。全16/898合法/score.375・Xi[0,.5,.5,0,.5,.5,1,0]・root16featureNNbit/教師16lineage対応を支持、時計資格unknown/NI0。game405.653584s/arena409.001613s/管理8job431.553877s、参照原因cleanup35.927621sを分離。元admit実完了欠測とpair1 IPC欠測は保持、原clock違反確定又は救済0。169最大1terminaleventdrain案を165同一ownerのNN0修復へ採用済、原結果と新adapterを分けて170実ORT/clock/条件付き4parallel実費へ進む。新独立検算の自動連鎖0。

165保存51442e06/metadata89de1eb1の自己必要Gitbytes・archive695ebae0/size・原/修復停止・backupを照合、168/169独立有限裁定と合わせ受入れclose。最小native忠実基準/16合法対局/教師16行に到達したが402実完了未記録・参照取消不足の旧16samewall資格はunknown、NI/最高棋力0。品質管理431.553877s/対局405.653584s/教師2.22行毎分、終端取消参照35.927621sを支配費の具体修復対象に採用。原StageA/16rawと新a78NN0修復を分離し、既配送170の実ORT採用/取消＋条件付き4arena費へ進む。次主評価mode/教師予算は実費で決め、旧16再実行・大棋力認定/Wasm入口待ち0。92 bounded-record適用は現在29.7MB/512KiBforecast・新runtime3220367/3220383の有限速報、自然observe/finish効果待ち。

92 bounded-records初回自然run0bd85f42はobserve＋singleinspect成立、12command/新保存約150KBでstorage効果を有限支持。ただしfinish05:56:09は残9.316606s/必要36sで拒否、notesbackup/全turn復旧は未成立。既92補足としてruntimepromptの終了余裕・短notes生成を実適用に結び、次自然tickでfinish成立を追う。新issue/強制tick/独立critic追加/guard時計緩和0。170実験は継続。

92 bounded-records/finish-first適用を有限受入れ。source8bbde3f6、current scheduler3228627/start26015831・monitor3228654/start26015854同boot alive、state running/ownednull/recoveryfalse、config契約loadedと24currenthash一致。32MiB/forecast512KiB/過去raw維持、保存cap効果と先行finishの未来効果は分離。次通常06:13:15頃のobserve/finish/backup＋新allocated増分で確認する。92長期停止責任in_progress/08時台4停止を維持し、正式全期間・外NN停止や棋力改善認定0。主170実測報告待ち、運用の全史監査/追加criticgate0。

06:27節目: root CUDA実演算成功を受領し、CPUORTのみとGPU全体利用不能を区別。170固定solo8+4arena32の40 COMPLETE/source bd7ffde0停止を現物照合、actualadmit/public/zeroは有限、exactkernelCPU/wholegame/NIへ格上げしない。保存移管forecast誤差44,255B guard不足は資源欠測として保持、科学結果の失敗へ付替えず現小保存引渡しを待つ。新hypothesis GPU最小同重み経路NN0選定とcritic nativeNI費用/valid停止規則独立設計を配分。GPUモデル実測/新正式対局はこの調査では開始0。主仕事はnative棋力判定と教師生成、GPUがCPU経路開始gateではない。旧600pair/5pp/95%は遡及変更せず、新方式の数学/仮定を独立確認後にのみ新data前採択。次判断は速報と170最終で単一native runを登録すること、計測連鎖を増やさない。92の06:13 turn interruptedはsemanticfinish/backup未確認として別保持、追加監査gate0。

06:33実配分: 新quoridor-4lc.173を同experimentへ170最小引渡し後のnative主評価準備として配分。3arena CPU2/4/6/6GiB（guard5.5）でCPU0監督余裕を残す。最大600pair/1200game capacity/qualityheavy3600s/科学07:55まで、必要統計172速報採択＋preregister前sciencegame0。有効な新停止規則が成立しない場合は旧方式を勝敗で救済せず新計画を明示して判断、oldrawと混合0。GPU171は軽い並行経路選定で開始条件ではない。今回正式holdoutにteacher初根π/zを残しても学習使用0。これ以上localclock/calibration issueを主作業の入口へ追加しない。

06:40 GPU171速報を部分採択し新quoridor-4lc.174同hypothesisへ固定ONNXfoldedtorchadapter→保存5input CPUORT/torchCPU/CUDAparity→各warm1/steady8batch1の総費を既推論枠内で配分。共用環境/取得0/GPU学習0、追加256KiB既16MiB予約内、CPU0heavy180s/RAM2guard1.75。173は新science前RAM4.5guard4へ調整し監督1/steward.5との合計8内、GPUjobはCPU0自然監督と非重複窓のみ。新GPUは主CPUformal版へ混ぜず、利益/数値で後続教師生成経路を判断。

07:03更新: 173新scienceは06:53:23 firstblock開始後6terminalを保存し06:53:42.574 BeadsreadtimeoutでCONTROL_OR_INFRA_UNKNOWN停止/全engineclose/remainingunknown0、block2開始0と本人報告。原登録2fc9821/全attempt保持。600pair中103のNN0生成上限失敗で品質未知幅が判定を阻害することを、coordinatorは新科学WDL未読のまま設計停止根拠に選定した。同173残費で原48/49失敗seed先頭各1の257→4096 continuation費/受理率NN0を調べ、新未来epochだけ結果前登録、旧開始済block再利用/科学成功補充0。統計式の成立とlatent入力分布/運用成立を分ける。174GPUadapterは本人NN0準備済・実NN未測、173物理停止中の現在窓でadmissionが成立すれば実測、正式CPUと非重複/ready待ちgate0。
92 finish先行の通常06:13 run26db8a4fを必要5JSONで確認: observe06:13:40完了、notes/backup exit0/reaped、self-finish06:13:57保存、旧巨大stdout保存なし・歴史104038400Bparentcharge保持。後inspectはnamespace guard拒否06:14:32、Appturninterrupted06:16:20を別保持。入場/先行保存の有限改善を支持、独立判断/report/wholeturn全期間成功へ格上げ0。追加stop-start/新監査役は不要、92長期owner/08時台終了責任不変。

07:16更新: 173の同entropy48/49ply各1のNN0 continuationはproposal348/408で初受理、追加費合計約554ms。WDL未読のまま、fresh entropy/domainによる新epoch2・4096上限・登録blockごとのlazy firstaccepted生成を採択。元generatorと同じ「pawn/wallどちらかの合法categoryが空ならproposal全体棄却」を明記し、この条件付き生成分布への推定として扱う。cap失敗/旧開始済3入力のsignature再利用は登録6品質未知で停止し補充0。oldepochの6terminal/controlfault/未開始1194/wealthを保存、copied e2 draftの旧manifest/497generated/ready日時は旧provenanceへ分離し、新seed/sourceを結果前固定。readfailure初回でallarena stopCurrent/次NN0を接続し、10秒・最大1readretryは資格の救済に使わない。CPU3arena/統計閾値/累積費/07:55終了は維持。
174は本人GPU1run42forward停止/5×3parity成功、CPUORT-CUDA差policy5.722046e-6/value3.576279e-7、steady中央値3.5707745/2.100652ms、coldCUDA613.673741ms。native JSON/IPC全経路・対局速度未立証のため173CPU backend変更0。次は正式epoch2の結果と実費を優先し、GPU輸送実測の自動追加0。

07:55節目:173 epoch2は事前規則SCIENCE_DEADLINE_HEADROOMで07:50:17に科学停止、33block/99pair/198game/95勝103敗・mean.47979798、NIwealth約1.88506/負方向約.43848で両閾値20未達、結論は不確か。全owner回収/537460NN返却/8268公開手は本人有限根拠、保存引渡し・独立裁定は別。残1002gameは未登録capacityでwealthへゼロ補完0、old6資格未知別。保存算術のみの175既criticへ120秒/2MiB/08:05処理08:10提出を配分し、33登録block品質分母・exact閾値・停止と必要clock集計を独立裁定、新NN/game0。173packをその全文待ちgateにしない。
次枠の主候補は新しい学習用lineageで少数native自己対局→全手π/rootNN/rootmean/zと視点を保存→game単位split→本PV学習/ONNX/独立arena接続。今回173正式holdoutは転用0。NIを通すまで同計画を反復することやNNUE主実装全面移行は選ばない。初期Sigma同等は未認定のまま、教師・評価基準の機構対応と動作を使って軽い学習準備を進める例外の費用は次許可枠で設定する。現枠の追加NN/教師生成/学習/GPU接続は配分0、必要保存/裁定と92停止責任を優先。
