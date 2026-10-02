# SIGMA-DIVERSE-PREFIX-INDEPENDENT / quoridor-4lc.122

**保存集計・棋譜・時計の有限支持。候補W4D0L12、16局すべてgoal終局、764公開すべて合法と独立に確認した。** 評価は現候補が両色で敗れる局面を検出している。一方、小さな改修の改善差を検出する感度、代表母集団への一般化、正式公平性・NI・Sigma同等は未成立。actual_go=false。新NN／モデルload／対局／holdout送信0。

受領12:29:34UTC、ready/show goal+self・pause無し・本人割当確認後12:32:42claim、開始報告accepted。相対の早い期限、処理12:59:34／新run12:54:34／提出13:09:34を維持した。119最終handoff Git `d4ee35ea518f818bb76be39c9bc592987f9b3ea7`、data/report `a5f3183e`、handoff SHA `1cacd67d196fc897a49e82ffd6a93405d30eb06bd1e8948721012a93327be6ae`、stop SHA `624c0728471aea3a389f68c0fe7d4b8a48b6afb0fdc3da804888447e69ad3b3f` にbind。実pair1 `8124d876`／pair2–8 `532c873` と停止account版を区別した。12必要runtime sourceは532版と実bytes一致、各pairの5経路bindingも今回読込版と一致。測定版差はseed確認・admissionの起動数保護・保存helperで、探索kernelの差ではない。

| prefix | 生成seed／既ply | 候補色1／色2 | 新公開手数 | pair Xi |
| --- | --- | --- | ---: | ---: |
| 1 | 31001／4 | L／L | 97 | 0 |
| 2 | 31002／5 | L／L | 97 | 0 |
| 3 | 31003／8 | L／L | 113 | 0 |
| 4 | 31004／9 | W／L | 76 | .5 |
| 5 | 31005／12 | W／L | 88 | .5 |
| 6 | 31006／13 | W／L | 130 | .5 |
| 7 | 31007／16 | L／L | 111 | 0 |
| 8 | 31008／17 | L／W | 52 | .5 |

ブラウザ内の自己PRNG実装で8prefix生成を再算し、全attempt0／総8attempt、P1/P2各4、非終端・一意・合法順・648特徴・history/keyが保存文書と一致。各ゲームを原prefixから全Action逐次replayし、色・手番・seed1979・public/SAB完成sequenceとAction・goal・最終key/総plyを照合した。既prefixのplyを新764手へ加算しない。全公開bodyのboolean/null、UTF8 bytes、最終stamp、公開後不変、producer identity/gen/epoch/prefix/history/model/limits/tokenも検査。late／初回無し／AI責任loss／infra未完了0、起動16／未実施0。判定算術は119集計関数を呼んでいないが、合法性・特徴写像は共有RuleAに依存し、独立ルール仕様証明ではない。

手NN7764（候補3584／参照4180）、startup48別、計7812が一致。旧117/118や他のWDLへ統合しない。相手t0<旧ACK429、自Worker旧ACK0後の次t0違反0、旧返却discard298。旧APIの開始終了区間が相手入力と重なる可能性を持つ観測292は、CPU同時実行や有効思考増の証明ではない。最大自待ち0.030ms。Worker停止は候補upper<=D380、参照upper<=D382／lower>D2、境界0。ACKwall>500は2。全公開最大426.190ms。初終offset校正を再算し、区間中心差は最大絶対0.002686msだったが、途中drift・hard realtime・内核CPUは未保証。保存API入口の402後／公開後開始は確実0・可能0（保存offset区間を各イベントへ適用する条件付き範囲）。API awaitとWorker停止・ACKwallを計算CPUへ変換しない。

全764採用sequenceについて、対応したcache検証終了stampがcutoff402前であることを確認し、採用sequenceとSAB Actionを照合した。保存publication完了markerの換算区間も今回は402を跨がない。exact Atomic store時刻は保存されておらず、これを全SAB命令の硬い期限保証とは呼ばない。ブラウザmainがJudge/clone/UTF8後stampを作り、Node毎手審判・時計・CP転送は無い。

結果前に各prefixから1件、奇数pair候補／偶数pair参照、P1をpair1/2/5/6・P2を3/4/7/8とした最大8sample規則を保存した。全8件で5184特徴bits／1096NN要素／888prior、shape・finite・strict[-1,1]・engine固有Action順・P2写像・独自softmaxとprior対応・完成cp訪問規約が通過。prior最大差1.387031e−6。候補edge和=sim−1、参照edge和=sim／root=sim+1を別に検査した。新prefixは固定NN参照0、動的自己整合8であり、外部NN数値一致・全764root・深部・欠測parentQ/rootQ値の補完は認定しない。

この入力集合では、候補色1W3L5／色2W1L7。4prefixで固定Sigmaが両色を勝ち、残り4prefixは同側winnerだった。従って「すべて先後だけで決まった」「情報価値が無い」という説明は保存結果に合わない。平均pair Xi=.25はこの固定集合・単seedでの候補の弱さを示す。ランダム合法生成と先後交換だけでは難度の均衡や改修感度を保証しない。とくに両色敗北のXi=0と同側勝利のXi=.5は、小さな改善が勝敗を反転する前に飽和しうる。1prefix1生成seed／探索1seedで、探索の揺らぎと局面依存性、機構の効果、残CPU競合を分離できず、764手や16局を独立なWDL標本へ変換しない。

次案は一つ：**prefix1・7（両色敗北、浅深の2例）と8（同側winner）で、現C1.5と未採用C1.0の一因子対照を固定Sigma相手に同じ新seed2098・同資源/時計で各色比較する、診断12局。** 新baselineも測り、版AB/BA順を事前交互化し、旧119/110成績は置換しない。これはC採用ではなく、既K32で差を持つ介入にWDLが応じるかの感度試験。Δpair Xiが複数prefixで同方向ならその係数因子を次の未見局面診断へ優先、訪問分布が変わってもWDLが全て不変なら「効果なし」を結論せず、この局面集合の粗い勝敗感度を再考する。新障害なら責任/未完了を残し係数効果としない。最小費用12局/6session、残ply最大から手のT費用は最大2252×.5=1126秒、startup・自己待ち・保存は別。6job各300秒のwall capなら計1800秒だが完遂保証ではない。選定済み探索局面・単新seed・C因子以外への感度は限界として残し、正式holdout/NIに流用しない。本課題では実行していない。

原8pairで両Modeldrop zero、全search ACK zero、main timer/message0、監視callback待ち、inner forced controlled0とouter ownedwait/remainingunknown0を別々に確認した。ownerの全21run process-metadata由来1517 identityと、自己の8pair process＋inner-stop callback由来1663は異なる分母（後者のみ202・前者のみ56）。双方現在不在を確認し、所有の全期間保証や自然停止へ格上げしない。原測定admissionはargv0識別であり、測定後proc/exe+argv guardのNN0成功で遡及成立とはしない。元setup必要memberと旧失敗はread-only参照保持。

自己はChrome NN0 2run計24.213366秒、推論/model/Worker/game0、観測全TID CPU2、全owned currentRSS最大1,401,651,200B、保存観測peak5,722,112B。static停止照合の初回はempty pending_messagesを数値0と誤認、summary初回はpair最大値を加算したため、原ログ/出力を残し検査器だけ訂正した。起動前runs親dir不足はChrome0で終了。全棋譜r1の成功を良好行で置換せず、r2は保存独立結果の再集計のみ。瞬間peak/短いmetadata command CPU/全host保持量保証は未確認、旧課金減額・追加予約0。

source/Chrome/監視子停止・入力afterhash・owned waitを本文前に固定し、必要小archiveの全88memberをstream復元照合した。必要入力・選定・独立結果・失敗・再現commandは[保存正本](../../research-data/ai-sigma/122-diverse-prefix-independent/independent-results.json)、[参照/停止照合](../../research-data/ai-sigma/122-diverse-prefix-independent/input-reference-manifest.json)、[自己停止](../../research-data/ai-sigma/122-diverse-prefix-independent/runtime-source-stopped-before-report.json)、[archive manifest](../../research-data/ai-sigma/122-diverse-prefix-independent/archive-manifest.json)。自己checkerは `tools/ai-sigma-diverse-prefix-independent/`、runnerの各started/process/logに実命令・UTC/monotonic・boot/PID/starttick・資源・exitを保存。再現は現在許可の新configで、同runner→browser.cjsを使用する。coordinator受入れ待ち、goal/他者close0。
