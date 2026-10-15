# 404.1 関連論理確認：既往2回集合によるroot exact WDL

**math_claim_clear=true、blockers=[]、ordinary=[]**。提示された縮約は以下の条件で成立する。一般の「零在庫全配置でDなし」は引き続きUNKNOWNであり、この命題とは別である。新source読取・solver・追加計算は行っていない。

## 成立条件

固定壁・零在庫の有限、決定的、完全情報、交互手番のゲームを扱う。合法辺・goal終局は盤面状態だけで決まり、goalをdrawより先に判定する。終局にはこのgoalと自動threefoldだけを含め、時間切れ・投了・別のply上限・表現overflow等を加えない。

入力は既にterminalでない合法履歴。現在rootの出現は1回か2回で、既往3回／既往goalによる終了を飛び越えた履歴ではない。状態同一性はresearch HistoryKeyと同じで、二pawn・手番・stocks・H/Vを含む。固定でない過去のwall/stock keyを、同じpawn＋手番だけで現在の入口に混ぜない。total_plyそのものを反復identityに加えない。

過去2回の同一key集合Eは非goal draw終端に置換する。rootがE内なら、同じ合法出辺を持つ初期専用コピーr*から開始する。このコピーに入る辺は作らず、通常のroot keyへの全再入場はEのdraw終端へ送る。goal終端はEより優先する。初期履歴の0回と1回は、その他の非終端頂点の扱いを分けない。

## W/Lが実threefoldでも保たれる理由

draw終端を勝利attractorの種にしない有限到達ゲームで、Wは「即goalまたは低rank L子を一つ選べる」、Lは「全合法子が低rank W」とする。勝者がその選択を守ると、敗者のどの応手に対してもrankが毎ply厳減し、goalへ達する。L rootなら同じ議論の勝者は相手側である。

その経路はグラフ頂点を再訪しない。Eへ入る経路はdrawであって勝利attractor経路ではない。rootを複製した場合も元rootはEなので、r*と元rootを別頂点にしたことによる実盤面再訪は勝利経路に入らない。

したがって各非goal盤面keyの新規訪問は高々1回。初期に0回なら累積1、1回なら累積2であり、途中threefoldは生じない。初期2回keyは避け、最後のgoalは反復より優先される。これで静的グラフのW/Lは実履歴付きゲームでも同じ勝敗を強制する。

## Dが実threefoldでも保たれる理由

非終端Dには、即drawを選べるかD子があり、L子はない。各側は自分の手番でその非敗手を選ぶ。双方がDを選び続ければgoalには入らず、有限の実盤面key集合内でいずれかが3回現れてdrawとなる。draw終端自体には次の手を要求しない。

相手がDからW子へ出れば、その子の手番側（こちら）が静的Wのrank戦略へ切り替える。ここはさらに強く言える。それまでのD内prefixで新たに2回になったkeyはD頂点だけで、勝利rank経路はW/L頂点だけを通るため、そのprefixとは再衝突しない。初期Eも避けるので、この戦略どおりなら勝利が実threefoldでdrawへ落ちることもない。Rootの「drawへ落ちても非敗」という弱い結論は十分だが、このD内prefixとの再衝突が起こり得るという補足は不要である。任意の寄道履歴や途中rootへ同じtableを再利用する場合とは区別する。双方について非敗戦略があるため、D rootの厳密値はDrawである。

## 結論と範囲

以上により、**このrootの無限到達ゲームとしてのexact WDLは、board graph・初期2回集合E・必要なroot初期コピーだけで決まる**。入力の他のkeyの0回と1回の区別はroot WDLを変えない。これは「実履歴を削除して通常探索へそのまま使える」という主張ではない。

途中局面を新rootとして再利用するなら、その時点で2回になった集合とroot例外を更新する必要がある。有限深度heuristic値、alpha-beta TT bound、勝ち手数の最短性、選択手や全途中局面への同じtableの無条件再利用は証明していない。原335 history依存draw60や前404のD0結果を変更しない。

## 実STOP

追加のtarget/source/data readerはNOT_ENTERED。論理確認・私有文書の有限境界は **2026-10-15T00:34:41.209546+00:00**、owned readers/children/jobs/handles/TMP/leases/waits/remaining=[]。本出力用の小stdlib writerだけをCPU7/AS512MiB/GPU0で直接waitする。元source readerSTOP00:29:20.507217Zを新しい読取事実として再使用しない。native・tests・Search・model・game・solver・新計算は0。

JSONはstdlib indent=2＋末尾newline、Markdownは手整形。旧report/control/STOPは上書きしない。親404のownerへこの関連結論を一度返し、人間ACKや新review親を設けない。Main/Git/Cargo/製品/生成既定・models/weights/seals、mixed/learner全prep/pipeline・323 USERPAUSE・旧RAW/FAILED/費は不変。

D-prefixとW/L経路の非交差を厳密化した最終論理・文書STOP：**2026-10-15T00:35:57.281074+00:00**。target/source/data readerは引き続きNOT_ENTERED、owned残存は[]。
