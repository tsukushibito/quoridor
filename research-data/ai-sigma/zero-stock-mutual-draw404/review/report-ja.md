# 404.1 零在庫の相互千日手：限定独立確認

結論：**review_clear、blockers=[]、ordinary=[]**。対象Pythonは実行・importせず、保存結果の集計とcoreの必要な合法手／終局処理だけを読んだ。この有限確認を崩す欠陥は見つからない。ただし、全合法壁配置で盤面drawが存在しないという一般定理は **UNKNOWN**。短い有効な証明も反例も本scopeでは得ていない。

## 固定配置内の有限結論

64個の異なる壁集合の保存結果は、非終端状態628,572、W=336,960、L=291,612、D=0。各配置でW+L+Dは列挙数に一致し、保存したBellman/strict-rank確認は全件true。内側analyze elapsed合計0.7385032909660367sは保存scalarの合計であり、process/controller/source費の合計ではない。実計算の再演は0。

64の内訳は**合法20壁配置63＋壁無し移動グラフ対照1**。position.rs:90–93の在庫保存条件はstock合計＋設置壁数=20なので、壁無しをstock=[0,0]の合法core局面として数えない。対照自体のD=0は移動グラフの事実である。20壁配置については衝突／交差／重複と初期双方goal可達を検査する現sourceに対応する。固定壁を置く途中の可達性は最終配置から壁を減らすと失われないため、初期駒を動かさず交互に10枚ずつ置くprefixも可能である。各graphは有効positionの上位集合を検査しており、各列挙頂点までのgenuine駒履歴を個別構成したとは主張しない。

## 幾何・列挙・逆伝播

- check_graph.py:24–52のH/V二辺、境界、壁交差・同方向重複条件はcore position.rs:106–118,140–154と一致する。Pythonの横方向の列挙順はcoreと逆だが、隣接関係と集合は同じである。
- pawn_moves:67–80は空き隣接への一歩、対面時の直線ジャンプ優先、背後が壁／盤外の場合だけ左右の迂回ジャンプを作る。core pawn_destinations:240–272に一致し、零在庫ではwall手は不要。ゴールはP0最下段／P1最上段である。
- 状態(a,b,turn)は異なる非goal駒位置と手番を全列挙する。各駒の壁だけのgoal可達領域に制限し、合法移動／ジャンプはその領域から出ない。非goal子も同じactive集合に属する。手番を含めた符号化は一対一で、反転も正しい。
- 即goalはW/rank1。子Lがある頂点をW、全子WをLとするremaining逆伝播は、手番相対W/Lの通常の到達ゲームに一致する。成功Wでは低rankのL子を選べ、Lでは全子が低rankのWなので、勝ち側の戦略でrankは毎ply厳減して有限goalへ至る。goal以外の合法子が空になる場合はsourceが拒否する。
- 残Dには即goalも子Lもなく、少なくとも一つD子がある。これが未分類領域の非敗閉包である。W/Lのrank条件と合わせて、単に有限深さで見つからなかった頂点をdraw扱いしていない。今回はDが0なので、draw候補抽出branchの新実証はない。

find_layout.pyは蛇行8＋固定seed54を生成し、元2配置と合わせ64。今回の固定結果は途中draw打切りなしの64件で、全壁配置の網羅ではない。layout-inputsの別読取や新生成は不要だった。

## infinity drawと履歴付きthreefold

Dがある場合、各手番側はD子を選べる。双方がこの非敗方策を続ければ非goalの有限状態集合内を進み、同じ状態が3回現れる。固定wall／stockではresearch.rs:32–47のHistoryKeyはこの(a,b,turn)と一致し、total_plyを含まないため、研究threefold drawに達する。相手がDから自らW子へ逸脱すると、その子の手番側はboard勝ち戦略を使え、過去履歴で早期drawになっても敗北は強制されない。外部ply cap／表現上限による実行中断はこの抽象ゲームの勝敗命題と別である。

反対にboard-only Wのrank証明は、**これからの経路**の反復を避ける証明である。選んだ低rank子などが過去に既に2回現れていれば、そこへの到達で第三出現drawになり得る。research.rs:452–461はgoalを先に判定するので、即goalを反復drawへ落とす説明ではない。したがってD=0は全履歴でdraw不存在を意味しない。原335の履歴付きdraw60は別subjectのまま保存し、盤面Lへ書き換えない。その旧成功suiteや旧RAWを再読・再実行していない。

## 一般定理の扱い

全合法固定壁配置・標準ジャンプでD不存在という一般化は採用しない。「各駒に壁だけのgoal経路がある」だけでは、相手駒によるジャンプ／迂回を含めた単調進捗の短い証明を与えていない。64配置のD=0はその欠けた一般証明の代替にならない。壁在庫が残る別ゲーム／別盤面のdraw例も今回の反例として持ち込んでいない。新solver、追加計算、依存取得、source修復、科学実行は提案・発行していない。

## custody・停止・引渡し

対象4ファイルとcore position.rs/research.rsの6 FileRefsはcontrol.jsonにSHA/bytes/modeとbefore/after一致を記録した。coreは必要短片のみを意味解析し、全source監査とはしていない。元rank配列を別保存して独立再計算した主張もない。

実selected reader STOP：**2026-10-15T00:29:20.507217+00:00**。owned readers/writers/children/jobs/handles/TMP/waits/leases/remaining=[]、canonical/hardware idle leaseなし。有限helperは直接waitで終了し、native/model/Search/arena/生成/fit/test実行0。最初の名前付きrgが存在しないhistory.rs/rules.rsでexit2になった事実、bounded previewのtruncationは保存し、現research.rsへ必要箇所だけ訂正した。不明な中間PID/start/boot、continuous peak、全作業費はUNKNOWN。

JSONはstdlib indent=2＋末尾newline、Markdownは手整形。手書きproduction/helper codeの追加はない。対象usageは一度だけ記録する。本人404.1だけを検証／backup／closeし、親404の現ownerへ一回返す。Main/Git/Cargo／設定採用は324、一般結論の採否はRootに残す。mixed/learner全prep/pipeline・323 USERPAUSE・製品／generator既定・models/weights/seals・旧RAW/FAILED/費を変更しない。
