# 169 native保存16局の独立裁定

2026-10-03 UTC、critic。契約 `8fa353a2d4e1d08d627ef939b7cea00b05920218`、親11。受領05:30:51.297794、ready/showでgoal/selfのpauseなし・本人担当・168 closed/自域停止を確認し05:30:56.337702 claim/静的開始。新NN/modelsession/Chrome/build/game/学習/GPU/取得/委譲は0。

**全16予定・898公開手は、独自算術と共有RuleA再生で合法なGOAL終局として有限支持する。独立W6D0L10、得点率.375。正式NI・同等・同CPU消費は未認定。** 機構168を再検査せず、その有限対応と今回の保存棋譜を合わせ、native忠実基準を探索的評価と小教師生成へ使う根拠はある。正式時計の検査完了時刻は欠測であり、`formal_ready=false`を維持する。

## 棋譜・分母・感度

8rawと8journalをreadonlyで直接読み、原コピー・全archive展開なし。独自checkerはowner verdict/checkerを呼ばず、凍結19275b3のgame/contextをNode VMへ載せる。全prefix/駒・壁・side・key、反復を含む合法履歴、保存当該key履歴回数、public Actionと最終prefix、CP世代・全root合法順・訪問数・argmax先着順・rootmean/rootSum、goal優先/200ply/合法手なしdraw規則による最終winner/ply/keyを対応した。実16局にはdraw条件での終局はない。各pair世代は1から連番、root辺訪問合計=rootN−1、rootN=simulation、mean=sum/N。履歴全体の保存はopeningにあり、各publicでは再生履歴と保存key回数を照合した。全deep探索/backup符号の今回再検算はしていない。

| pair | opening ply | Xi | 同盤面側winner | 候補両色 |
| --- | ---: | ---: | --- | --- |
| 1 | 12 | 0 | いいえ | 負 |
| 2 | 13 | .5 | はい | 1勝1敗 |
| 3 | 24 | .5 | はい | 1勝1敗 |
| 4 | 25 | 0 | いいえ | 負 |
| 5 | 12 | .5 | はい | 1勝1敗 |
| 6 | 13 | .5 | はい | 1勝1敗 |
| 7 | 24 | 1 | いいえ | 勝 |
| 8 | 25 | 0 | いいえ | 負 |

Xiは2色scoreの平均。層12/13/24/25は各4局、score .25/.50/.75/0。同盤面側winnerは4/8、候補両色敗3pair・両色勝1pair。盤面側支配による感度不足と、8pairの標本不足を区別する。16独立位置/IIDを証明せず、W6L10を普遍劣性や即仕様変更の根拠へ変換しない。old149/151/browser成績との合算0、診断opening/教師を正式holdoutへ格上げ0。

全予定運用と双方正常terminal品質はいずれも16/16。再生で確認したcandidate fault/reference fault/infra/未開始/未完了は各0、未知運用score0、全予定score識別区間は[.375,.375]、complete-only補助も同値。これは母平均の信頼区間ではない。正式な402ms検査完了資格を要求する別のscoreは未確定であり、その認定をしない保守的全予定未知範囲[0,1]を別に残す。時計欠測を原棋力lossや反証済み違反へ付替えない。

## 時計の有限支持と具体不足

controller単一Node hrtimeのt0、受信、採用記録、public、quiescence gateを比較した。Python worker elapsed/API process CPUをcontroller epochへ換算していない。

- 全898採用CPは同世代・合法で、保存receive≤`admit_ms`≤402ms、公開時刻以下。公開actualは409.298677–418.699164ms、全件500ms以内。
- 411msは予定public、actualは上記範囲。402msも予定cutであり、actual stop送信は400.186749–411.511414msだった。Node timerのactualを登録値と同一視せず、記録上の採用判定は別に402を用いる。旧数値/規則を救済目的で変更していない。
- 次actualt0は前result/zeroをawaitしたgate以後、最小gap .146706ms。各rowでactiveNN0/handles0/activefalse。公開後cleanupを原因側の別費用として待ち、相手の新持ち時間へ加えないnative modeの有限証拠である。kernel CPUの厳密帰属・途中drift・全hostをこれで証明しない。
- pair1の105行は`quiescent_receive_ms`がpostpublic gate観測で、実IPC受信時刻は欠測。erratumを維持し補完しない。pair2以降793行はreceipt/gateが別でreceipt≤gate。修復は時計政策変更ではない。

**重要不足:** `arena.cjs` callbackの`const end=now(), v=admitCP(...)`は、legal/schema検査の前にendを採り、さらに`structuredClone(x.cp)`とcache代入はその後である。従って`admit_ms`は実validation-end/cache格納完了の証拠ではない。最も境界に近いgame14、ply46、reference、generation72はreceive401.983738ms、記録stamp401.999397ms、402まで.000603ms。実操作完了時刻がないため原違反確定にも救済にも使えない。500ms内の公開は確認できるが、既登録『legal validated≤402』の正式成立は保留する。未来の修正版では検査とimmutable copyの後に実完了stampを採り、同一402判定を両engineへ適用する記録修復が必要。今のraw・勝敗は変更しない。public actual stampもfinalization操作直前であり、厳密操作完了の全証明はない。

## 初根・版・停止binding

初根16は各gameの最初の手番rootであり、8openingについて色交換でC/R双方を対応する。再生state/key/full opening history/side/features648/合法順を固定入力へ合わせ、保存NN137 f32 bitsは各pairで一致。backend内の保存対応で、今回NN推論を再実行したものではない。途中全NN/全deepの一致は認定しない。shared RuleA、保存trace、元NN実行基盤を共有する独立性限界がある。

入力SHA `7cd2fe2470792a9e1ac2de381ec8a89974f78c4844a943758ec82147c0c0a5d5`。8raw/journal SHAはreplay-result、run inputs/source SHAはbinding-resultに保存。pair1は19275b3、pair2 e6b42a3、pair3–8 f63e8b3の実source/Gitblobを対応。arena/clock/engine/ORT/game/context/native referenceの必要blobをsaved inputsに照合した。StageA a09279cをStageBへ付替えていない。166のnative timer除去裁定・168のStageA機構対応を参照し、固定Web751186のnative-hosted JSをSigma C++/製品browserと呼ばない。

実metadataはORT1.30.0 CPUExecutionProvider、intra/inter1、SEQUENTIAL、affinity[2]、16session（8arena×2）、固定ONNX SHA `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d`。165 science-stop SHA `9becd64e4bfac3e3d145765a7586b0e3376ac49aaae87d5b6ebdb7d49aac671c`を現物確認。8管理job exit0/remaining[]/unknown_adopted[]、model/engine終了receipt0、observer callbacks待了・pending[]・timerfalseを照合。runner/rootと保存engine/model exact PID/starttickの現在同identity不在を確認。sampled合計RSS最大950,575,104B、原guard5.5GiB内。これを瞬間peak/全host/全期間自然終了保証にしない。原NN0 oracle affinityguard SIGTERM、165pack/helper継続と科学停止は別scopeである。

## 分母と費用

| 分母 | candidate | reference |
| --- | ---: | ---: |
| API starts（hand NN） | 18,471 | 21,907 |
| 採用CPまでのNN | 18,048 | 21,415 |
| 採用backup/rootN | 49,857 | 64,527 |
| 最終completed backup | 49,937 | 931,260 |
| completed terminal-noNN | 31,835 | 909,800 |
| pending NN返却discard | 369 | 447 |
| CP received | 49,937 | 931,260 |
| CP admitted | 49,857 | 64,527 |
| late CP discarded | 80 | 866,733 |

各rowでcompleted=starts−discard+terminal-noNN、CP received=admitted+late+schema、schema reject0。hand NN40,378、startup16は別。最終completedにlate backupが多く、採用探索量へ混ぜない。C/Rで対局経路が違うためNN総比を因果・同仕事量・同CPUへ変換しない。

16game時計405.653584秒（平均25.353349秒、56.125手、.039443 game/s）。8arena409.001613秒（.039120 game/s）、8管理job合計431.553877秒（.037075 game/s）。arena−game3.348029秒は起動/終了/間処理の合計で、全部をモデル初期化と呼ばない。ORT内部init16件合計.460949秒、startup16壁時計.106056秒/API .088337秒はその内訳であり重複加算しない。outer管理overhead22.552264秒はBeads observer/回収等を含み、NN処理時計と区別する。全研究LLM/保存packまでの費用を包含した値ではない。

hand API応答合計230.871891秒、NN pipe合計303.570873秒、差72.698983秒は当該NN転送/待ち/wrapper区間の集計で、候補Rust IPC/合法性/BFS/全JSON/CPU費の完全分解ではない。Python process CPU補助159.643228秒はkernel全CPUへ変換しない。journal保持3,057,214B、原8raw645,156B。生CP JSON輸送byteは保存欠測、981,197 CPという回数と毎backup全root_edgesをserializeするsourceだけを根拠とする。

速度維持を仮定した1200game対局部分8.4511h、管理job部分8.9907hは今回単arenaの参考。opening/熱/並列倍率/保存変更に依存し、正式実施費保証でなく、旧browser費や単独/並列と合算しない。

後着教師16行は8game-pair lineage、train14/validation2（pair6）で同group split混在なし。πを採用CP辺訪問/辺合計から再計算、rootmeanとrawrootNNを分離し、game zをopening手番とp1へ独自変換して原winnerと対応。sideは0-based export、playerは1-based。全16のraw SHAとopening history/featuresも確認。leaf_nnは欠測、zは実対局結果、πは可変rootN、formal_holdout=false。16行/8groupは学習readyや汎化棋力の証明でない。対局時計換算opening教師.03944行/sで、全手898行をexport済みとは扱わない。

## 最大1次案

**private native参照のterminal-noNN連続処理に、有界event-loop yieldと取消点を入れる小修正を推奨する。** game7/8/11/15/16の5要求で公開後cleanup合計35.424240秒（今回game時計の約8.73%）、最大10.495238秒。保存表の各要求内訳はbinding-resultに保持する。全reference late866,733件のうち、この5要求は863,805件を占める。全reference原因側cleanupは35.927621秒、candidateは.193535秒で、上記5要求の部分和と分ける。

sourceではterminal leafがNN awaitを通らず同期loopを続け、stdin stopのeventを処理できない。watchdog10秒/大量CPは保存tailと整合する構造的説明で、NN推論自体が遅いという診断ではない。有界yield（例: terminal連続chunk32回または2msでsetImmediateしてstop処理）は毎simulation browser timerの復活を要さず、取消遅延と不要CPの総費を減らす狙い。具体chunk値・overheadは未来版の実測で固定し、性能改善をまだ認定しない。candidateも同じ取消/公開規則に揃え、旧policy/prior/勝敗を修正しない。

次ownerへの最小成功基準は、保存terminal状況を使うNN0有限mockで取消到着からloop停止/最後CP/result/zeroとJSON数を記録し、長tailが消え、seal後のNN開始0、採用手変更0、既探索算術が維持されること。新版/rule/provider/clockをWDL前に固定して初めて少数診断へ進む。機構全再認証・全史・静的検証の自動連鎖をgateにしない。時刻記録修復と正式mode/statistical manifestは必要不足として残し、正式NIは別計画。今回169で修正や実験を開始していない。後着165本人報告ではa78ea8336edc84c9716fee8972c86d94200941b6の両engine per-CP setImmediate/actual completion rollbackをNN0 control・保存tapeで確認中。これは原StageBの科学成立へ遡及しない。本提案と同じ取消不足に対する既owner作業なので二重の新修復や相互受入れ待ちを追加しない。全CPのyieldはterminal連続chunkより広い措置で、同K対応と同wallでのoverhead/実ORT取消は別。165本人修復報告は独立再認証ではなく後着metadataとして保持する。

## 自域検査・引渡し

再現: `taskset -c 0 python3 tools/ai-sigma-native-games-independent/managed.py replay-r1 node --max-old-space-size=256 tools/ai-sigma-native-games-independent/replay.cjs`、同managedでbinding-r1/Python。r1はいずれもexit0、科学再実行0。追加の世代/分母/初根対応・独立action136変換/P1視点はaux.cjsのaux-r1で確認し、aux-resultを正本とする。先行短い追加分母算術の結果もdenominator-resultに残す。CPU0単1、sampled親子RSS replay140,034,048B/binding49,188,864B、guard896MiB内、瞬間peak不明。先行管理を20秒保守計上し科学脚本合計24.819638秒。read/報告/Git/backupの管理費は別停止記録へ追記し総180秒を守る。初期保存account current＋forecast93,318,278B<critic112MiB guard、未知旧量を減額しない。停止・Git必要stream復元・Beadsnotes/backup・coordinator報告はhandoff記録を正本とする。受入れ/closeはcoordinator、goal/他者close0。
