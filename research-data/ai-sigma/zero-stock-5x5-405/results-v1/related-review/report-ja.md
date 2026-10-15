# 保存D局面と初期在庫3ずつの具体例

**interpretation_clear=true / blockers=[] / ordinary=[]。** 固定completionはSHA256 `f46610b9351a420ee4508e368df8cac0c8f2a3ca20d1da37d435a790302ae9c7`、10317B、0644。今回の限定結論は、保存された5×5の盤面Dが存在し、双方初期在庫3・通常の初期駒・P0手番から、既往二回の罠なしに双方在庫0のDへ合法に到達できる、ということである。

## 盤面Dの証拠

保存graph `4e2e7aa3…` /11908Bはmask67882、active610、合法辺1460、W330/L258/D22。最初の保存Dはraw315のままで、今回のprefix到達先raw376へ付け替えていない。元の独立参照はこの同一SHAの全合法辺・WDL・rank・D選択を照合してexit0、cleanuptrue、primarynullで終了している。今回、その参照コード/solverは再実行していない。

独立に行ったのは小さな保存binaryの読取りと、既存ラベル/rank/辺の整合確認だけである。全Dにはgoal辺/L子がなく、D子があり、保存choiceもD子である。Wにはgoal又はrankの低いL子、Lの全子にはrankの低いWがある。幾何から合法辺を再生成したり、WDLを再計算したりしていない。合法辺の完全性は元の独立全graph照合と、既に確認した不変の規則源泉に依拠する。

Dで各自がD子を選べるため、双方に非敗戦略がある。全応手がDという主張ではなく、次手番側のWへ出る負ける逸脱もある。どちらも相手のgoal勝ちを強制できず、D内を続ければ有限個の盤面＋手番が反復する。goal優先のthreefoldでは有限のdrawになる。これはdepth/node capによるUNKNOWNではない。

## 12手prefixの具体的確認

座標a..e/1..5、P0 goal=5段目、P1 goal=1段目、初期P0=c1/P1=c5、P0手番、在庫3ずつとする。

1. 空盤でP0 c1→c2、P1 c5→c4、P0 c2→d2、P1 c4→c3。
2. P0から交互に H b1、H d1、H b2、H a3、H d3、V a1。bit順1,3,5,8,11,16で、3枚ずつ使い切る。
3. P0 d2→c2、P1 c3→d3。保存辺raw424→375→376と一致し、到達先はP0=c2/P1=d3/P0手番のD。

最初の4歩は空盤の通常一歩で、jumpやgoal着地を含まない。6壁は相互に重ならず、交差もない。壁を置いている間は駒がd2/c3で固定され、最終壁下でもP0のwall-only path `d2→d3→c3→c4→c5`、P1のpath `c3→b3→a3→a2→a1` が残る。従って、壁がその部分集合である各途中配置でも両者のgoal pathが残る。wall-only pathが相手pawnを通ることは、壁配置の可達条件に反しない。最後の2歩も開いた通常辺で、相手駒への着地やgoalはない。

保存した12 actionsと13 history keysについて、手番交替、移動側、stock減少、mask追加、駒位置と保存graphの子IDを照合した。stockを除いた `(壁mask, 両pawn, 手番)` でも13件すべて一意で、最大既往回数は1。過去二回の入口を利用したdrawではない。最終壁を初期位置へ先置きする案はraw144がinactiveになるため不成立であり、ここでは採用していない。

Dの保存choiceは376→427→428→379→368、その後368→319→316→367→368の4手周期。traceの全辺/子ラベルは保存graphと一致し、goalなしで三回反復へ進める。周期を強制する一方的戦略と主張する必要はなく、相手がDを選び続ける場合の一例である。

到達直前の値は手番相対で **raw424=W、raw375=W、raw376=D**。最後の2手は勝ちを保証する選択を見送っている。従って、このprefixは合法な到達可能性の証明であり、初期局面からの双方最善playや初期WDLの証明ではない。

## 集計・限界・費用

全2532560集合/841986100局面/1838022824辺、W485420844+L356525548+D39708=841986100、Dを含む3872集合という既存censusは、固定の作者受入れを再利用した。今回確認したsmall summaryでは、pilot634+補集合2531926、5streamと壁数別の総和、固定48B行の長さ、D集合数も整合する。121MB recordsの全再decode・全配置再監査はしていない。D存在の限定結論は当該graphと具体prefixだけでも支持される。

9×9/20壁の埋込み、他の初期在庫値、全履歴の一般定理、初期からの最善playはUNKNOWN。製品のルール/既定値/model/TT/探索へ採用していない。元Rust16e4/reference34b/sourceSTOPff2150/software7+52のscopeは変更せず再演0。元native費・FAILED/RAW・returned completedとdisk pending/attemptedの区別・capture erratumも保持した。今回のsaved helper費は元native/outer費へ加算せず、全作業費とcontinuous family peakはUNKNOWN。

## 停止と引渡し

選択8参照のSHA-size-modeをparse前および読取後に照合。実selected reader STOPは **2026-10-15T03:04:31.730917+00:00**。各readerはdirectwait/reap、fresh identity absent、handles closed、readers/children/jobs/TMP/leases/waits/remaining=[]。詳細は同dirのSTOP.json、saved-checks.json、read-receipts.json。以後の報告/管理で元payloadを再読しない。

本有限関連phaseの結果をcurrent324と405.1へ各一回返す。一般理論/親close/返信ACKを追加条件にしない。mixed/learner全prep/pipeline、323 USERPAUSE、models/defaults/weights/seals/旧RAW/FAILED/費UNKNOWNは不変。
