# 凍結真正z NNUEとDの同完成depth1（301）

4 prefix×2評価器の全8検索がdepth1を完了した。入力は300結果前freeze5be19b4dの先頭4 index [783,784,670,671]をtarget-free参照だけから解決したもの。同じ2familyのply10/11、P1/P2各2であり、4独立gameではない。301では終局target・sealed raw・新game・Torch・新モデル・buildを使っていない。主候補は298 BEST1000/128000seen（全学習run1000064seen）のmanifest3177ff54/weights1f8d8c28、対照はraw D a0,b8。

|root/STM|NNUE Action/PV|D Action/PV|NNUE値|D値|nodes NNUE/D|非terminal eval NNUE/D|
|---|---|---|---:|---:|---:|---:|
|0/P1|125/[125]|133/[133]|.044328284|.197375312|106/105|105/104|
|1/P2|140/[140]|58/[58]|.214728355|−0|103/102|102/101|
|2/P1|117/[117]|13/[13]|−.353289455|−0|102/99|101/98|
|3/P2|140/[140]|140/[140]|.675504804|.291312635|103/102|102/101|

全検索requested/completed depth1、StopReason DepthComplete、全PVは1ply。3/4のAction差は評価器が手選択へ効いた観測で、正しい手の証明ではない。main CLIの全rootchild exact列/argmax集合はNOT_RECORDEDなので、順位差の完全分解やbadmove真値には使わない。300新96familyのz差CIが0を跨ぐ有限結果と合わせても、正式強度や十分量は認定しない。

maintained nnue-diagnose6a2fc4fをgeneric --config、distance_residual/D、全合法・履歴を保持する既αβで使用した。入力sideとP1P2→STM sparse IDs、distance f32bits、state key、完全history literal、prefixを出力と一致確認した。root・親history復帰、選択されたpawn/wall childのfull/delta toleranceもPASS。depth1ではsource negamax depth0で非終端葉を評価し、terminal±2を先に処理する。現在sourceにextension/reductionはなく、1着手=1plyの有限horizonを共有する。PVSのnullwindow→fullwindow再検索は現実の仕事として残り、NNUE/Dのnodes差を速度化や深い読みへ読み替えない。全8 TT_hitsは0、NNUE delta_updates=410。TTやorderingの一般的価値をdepth1の0hitで否定しない。

実科学は22:38:19.881922→22:38:20.000496 UTC、PID2015829/t49296324/CPU3、exit0・全wait/currentidentity/pgrp不在。456NNはsearch410＋root/選択child parity46、D NN0。processed822は全search node。MAX1は消費し、2000NN/5000processed予約・元donorの費/UNKNOWNを保全する。whole caller guardian.122956106秒とnative.06279524秒は包含spanで加算しない。per-search時間はNNUE .000623/.000214/.000176/.000174秒、D .000256/.000410/.000132/.000120秒。固定NNUE→D順でcold/load・cache・短い計時の交絡があり、比率を本番支配費や速度優越にしない。callerには入力復元・モデルload・選択child parity・search・出力が含まれる。管理者+familyのsampled peak26.5MBは短samplingで、全過去peak保証ではない。native自身も448MiB guard内で処理した。

次の最大1は、凍結モデルを変えず新事前固定opening/colorで同100msの小paired対局を行い、実手選択が終局効用へ移るかを直接問う案を優先する。今回のengineering接続成立と、300のz MSEの不確かさは、その品質観測を省略できる理由ではない。一方で対局小成功を必要true-family量や表現改善の入口gateにしない。新8opening×色交換=16gameのpilotなら、200ply×100ms×16=320秒のsearch clock上界に準備/検証/初期化/回収/記録を加える。各root maxnodes2048の場合、PVS含む保守NN上界を2*2048+1とすればNNUE100手/game×16で6555200、初期parity/非対局forward等を含め約6.56mが仮のadmission案。source/library actualcallerに合わせた再束縛が必要で、生成NNと学習samplesの費単価を同じとしない。CPU1、RAM512MiB、出力/prefix/scalars/archive/Git/tmp 8–16MiB、準備10–30分、科学320秒+guard回収程度を概算とする。未知は終局到達率・node capで完成できるdepth・中盤/終盤caller費で、旧500k capが全予定をcensorした運用知見を残し全16planned/UNKNOWN/NOT_STARTEDを保つ。16gameは強度precisionの十分量ではなく、条件を結果前固定した実用pilotである。本301から新対局を開始しない。

位置付き経路/壁効果・history/leaf-targetは、同完成depthの数値/手が真のcounterfactual値へどう結びつくかと独立に有力である。今回parityが成立しただけで入力十分性は認定しない。true-family増量は576既見trainから新96へ移る不確かさとearly BEST/late fit差が根拠で、同seenと量に応じた仕事を分けて再検討する。ordering/TT/allsearch費も別候補だが、このdepth1の6node差やtiny wallだけから大きな改修の回収は決められない。次pilotで完成depth・NN/wholewall・censorが効用差を支配すれば、history-key完全性を守ったTT/ordering費へ優先を変える。手の効用を問わず追加LR/seenだけ循環しない。

source/configはRuff format/check/lint、合成NN0 fixture7件（schema/深度未完/P2/history/親/NNcap含む）を通した。native argv/stop enum/出力schemaはsourceから事前確認した。source-reader-stop、原raw出力・counter・purpose結果、6member小archiveのstream byteSHA復元を保存した。main/Rust/依存/Git/indexの編集はなく、統括が明示保存を所有する。92のfresh22:35 coverageとowner予測でold29932→30+new2MiBを保存し、元298/300/299の成功・失敗・UNKNOWN・開封済みprotocolは変更していない。
