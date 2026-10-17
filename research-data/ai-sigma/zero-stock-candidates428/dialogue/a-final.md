# 428.1 A 最終：壁ゼロの安い確定条件、相互批判後の一度の改訂

初稿7方法族と相互批判を保存したまま、優先を4案へ統合した。第一は既存距離表と一本の経路時刻、第二は真正goal/標準壁の距離1 terminal-tail、第三はcross sentinelによる別component、第四は同じwinning witnessに対するfuture-phase E資格である。gate/DAGは経路法の費用を変える実現形で、別の新coverageへ二重計数しない。

**条件付き十分性の論証、保存された有限照合、実装/性能の未確認を分ける。whole速度・棋力・採用は主張しない。** 今回はMain/Git/Cargo/source/observer/cache/production/model/Search/game/fit/Perfを変更・発行していない。新しい未来のseed/config/model/Experiment/runtime参照も作らない。

## Bの指摘への対応

| 自分の初稿 | 対応 | 最終的な扱い |
| --- | --- | --- |
| A1 即時goal/terminal predecessor | 受入れ、distance1補題を独立確認 | legal goalを維持。標準壁/N>=3/stock0の最大3ply方策を同族へ統合。途中historyは別 |
| A2 component | 受入れ | cross unreachableのみ優先。完全IDの新owner/償却を無料としない |
| A3 path/DAG/gate | 受入れ、gate資格とparityを追加 | 元phase式を相互確認。G-geodesicとrestricted routeを混ぜず、色で二hazardを分離 |
| A4 corridor | 未証明維持 | 全退却/side/exit/goalを扱う一般rankは無い。局所lemma以上へ広げない |
| A5 root separation精密化 | 数学維持、重点から棄却 | 427の9x9失敗12はrhoでも救えず、old414/424撤去を維持 |
| A6 小さい両者non-loss | 条件付き論理維持、資格追加 | 全off-cycle出口とsame-domain proofが必要。安いS未発見で優先外 |
| A7 E回避 | phase精密化を受入れ | 初稿cellmaskも安全だが、current/goalを除くfutureQへ精密化。API/実費は未知 |

A6のown-goalは非敗戦出口、opponent-goalは拒否と明記する。単一D-safe traceや無資格の保存ラベルをcurrent contextの出口へしない。一方、**正しく束縛されたboard non-loss strategy**なら、途中にhistory Drawを追加しても非敗戦は壊れない。これはboard-Wをreal-Wへ昇格する主張ではない。Bの注意を未資格label禁止として受け入れ、弱いnon-loss命題へのこの補足はAの説明として区別する。Bの最終回答をまだ見ておらず、この補足の明示合意を捏造しない。

## 1. phase付き経路を、格子色でさらに分ける

固定壁の普通の無向単位辺グラフGで、候補勝者wの位置aからgoalへ至るsimple shortest pathをP=v0..vn、n>=1とする。相手qの初期位置b、相手のown ordinary goal距離d_q。w先手δ=0、後手δ=1。w到着前のq手数はr=n-1+δ。

各点の真の距離下界ell(v)<=dist_G(b,v)を用いる。既存の正しいsame-wall/size/goals/ownerのpairなら

ell(v)=max(Manhattan(b,v), 有限な|D0(b)-D0(v)|, 有限な|D1(b)-D1(v)|)

でよい。各row両端が正本sentinel未満の項だけ使う。pair不在/不一致をunreachableへ変換せず、cross取得のためdistance()を再呼出ししてBFSへ進めない。

A/Bが独立に導き相互に確認した基本条件は、d_q>r、0<=j<nのell(vj)>j+δ、endpointのell(vn)>r。δ=0,j=0はManhattanを含むため自明、δ=1,j=0は最初のq jumpを排除する。相手の手**後**の隣接は許す。B3の「no-first-contact」という名称より、「最初の相手jump・指定route占有を排除する経路」が正確である。AのStage2固定例は、条件通過なのに初期/相手ordinary手後に隣接するもので、誤WDL反例ではない。

### Bの新parity提案を独立に確認した

χ(x,y)=(x+y) mod2、p=χ(a) xor χ(b)。ordinary移動だけが各色を反転し、stock0でpassが無いことを使う。goal distance値のparityを座標色の代わりにしてはいけない。

まだqの最初のjumpが無くwがPをordinaryで進む間、qのt手目前にはwはv_(t-δ)、qはt-1普通手済み。二駒の色xorはp xor1 xorδであり、隣接の必要条件はp=δとなる。一方、wのi手目前のq色とtarget viの色が一致する必要条件はp!=δである。色条件は必要条件であって、壁を越えた実到達を保証するものではない。

従って次の二場合で十分である。いずれもd_q>rと完全なhistory資格を別に残す。

| 色の場合 | 必要な下界検査 | 色で消えるhazard |
| --- | --- | --- |
| p=δ | ell(vj)>j+δ、0<=j<n | qのjump前には全target占有が不可能。endpoint占有式を省ける |
| p!=δ | ell(vi)>i-1+δ、1<=i<=n | wがordinaryを続ける限りqの最初のjumpが不可能 |

p=δでは、targetが空なのでwのordinary方策を継続できる。qのt手目が最初のjumpなら、qのt-1普通手とwへの隣接辺でdist(b,v_(t-δ))<=tとなり、ell>tと矛盾する。p!=δではtarget下界が占有を排除してwのordinaryを保ち、その間は色でqの最初のjumpが不可能。両場合とも帰納が閉じ、qはr普通手でd_qへ先着できず、wは先にgoalへ着く。jumpを普通一歩として数える循環は使わない。

これがB提案へのAの条件付き独立確認である。stock>0の壁手やpassを許す規則では色が反転せず使えない。w自身が適当にjumpする方策へ置き換えても使えない。endpointを省けるのはp=δの場合だけ。実到達不能表現とgoal/threefold優先も保持する。

この弱化がそのまま一手分の追加coverageを生むとは限らない。Manhattan/正確rho自身には既にpoint-to-point parityがあり、有限goal差はそうとは限らない。今回Aは新しいparity board censusを実行していない。Bが既に選択した固定171に新述語だけを一度当てるなら、その実結果はBの最終報告の範囲でのみ扱う。

### 一本/DAG/gateの費用と資格

第一案は既存mapから決め打ち一本を選ぶO(n)方式。最大4n程度のedge/gradient検査、各点ellの2row読取/finite/maxがあり、n<=80でも無料ではない。既存TT hit/旧M成功時の追加仕事は避ける設計を望むが、実sourceは変更していない。geometry成功で増えるE scan/TT leaf storeも費用に含む。

safe shortest DAGはi=n-D_w(v)で時刻を固定し、最大81頂点と辺のDPでsafe一本を探せる。全path列挙は不要だが、visited/viable/witnessのO(N)一時保存と走査を要する。一本の失敗は全DAGの失敗ではない。Bの固定集合ではDAG/exactrhoの追加0だったので、今その費用を先に払う根拠はない。

gateは二種類を混ぜない。

- **G1 path上gate。** c=v_tがbと全suffixを分離し、subpath c..viがG全体のgeodesicならdist(b,vi)=dist(b,c)+(i-t)。全PがGのshortestならsubpathもgeodesicである。prefix検査とell(c)>t+δでsuffixを圧縮できる。単に通路内最短では等式が未保証。a=cはt0、c=goalはendpoint式、qが既に領域内なら拒否。複数入口は全入口のmin。
- **G2 protected chamber。** aとgoalと全pathがS=component(G-g)内、bは外かつg以外。H>=rとd_q>rで十分。qの初進入/jump前にgへ居る必要があり、その時点は最大r-1普通手だからH>=rに反する。最後のordinary手で初めてgへ来てもqの次手は無く、wはS内goalへ着く。nはrestricted pathでよく、global D_w(a)を代用しない。

G1のstrict閾値、G2のnon-strict閾値、path上/外のgateを無条件に入れ替えない。どちらもarticulation/component/restricted mapsのwall前処理・保存・key/gate identity・寿命が別で、既存full-G pairの無料aliasではない。現段階ではF1の保留した圧縮実現形に置く。

## 2. 標準壁の手番側distance1は最大3plyのboard W

Bの補題を独立に確認した。盤サイズN>=3、対向goal rows、標準長さ2壁、双方stock0、合法非終端かつ双方own-goal reachableという前提が要る。**手番側**のordinary own-goal距離ds=1に限り、非手番側distance1へ一般化しない。

goal隣接の現在位置をx、そのgoal cellをyとする。yが空ならordinary goal。相手がyを占有しても、yの左右にopen edgeがあればsidejump着地も同じgoal rowなので即勝ち。

即勝ちが無い場合、yのside辺は全て壁/盤外で閉じている。goal rowの横辺を塞ぐ標準V壁は、隣接rowのxの同じ横辺も塞ぐ。盤端側も両rowで盤外なので、yはdegree1で隣xだけ、xは横へ出られない。

xの後ろzへの辺が閉じていたら、相手はcomponent{x,y}から対向goalへ行けず、own-goal reachableに反する。従ってz辺はopen。すると初二手は強制である。

1. w：x→z。yはoccupied、straightは盤外、sideも閉じているので他の手は無い。
2. q：y→x。wは二辺離れたzにおり、degree1のqにはこのordinary手しか無い。
3. w：z→yとqをstraight jumpしてgoal。wが選べる合法勝ち手である。

N>=3なのでqの中間着地xはqの対向goalではない。上下反転も同じ。N=2、任意graph、非標準壁、positive stock/pass等には適用しない。初稿E2の「ds1だが即goal無し」は保たれ、これをboard-L反例にしていなかった留保も維持する。

### 履歴は二つの中間keyで分かれる

K1=(w=z,q=y,turn=q)、K2=(w=z,q=x,turn=w)は異なる非終端key。完全canonical aggregateで両prior count<2なら途中third arrivalは無く、実Wである。E空は十分だが、無関係なcurrent count2まで拒否する必要はない。key生成・count取得・make/undoに既存ownerを使う必要があり、無料ではない。

sealed caseでは初二手が強制なので、K1または到達前K2がprior count>=2なら、そこで真正threefold Drawとなる。これはAが導いた条件付き帰結で、Bの最終版でこのDraw拡張まで明示受入れされたかはまだ見ていない。勝ちへ丸めず、time/nodecap UNKNOWNをDrawと呼ばない。現SafeRaceLeafの±専用意味へ0/片側non-lossを混ぜる変更も今回認定しない。

最小の次確認は既存sealed endpoint169への新補題、上下反転/side-open/盤サイズ>=3、K1/K2のprior2・base+overlay境界。これは検証計画であり、新source/jobを発行していない。通常全合法goal手の処理と重複する費用も後に必要である。

## 3. 既存cross sentinelによる別component race

正しいown finite値に対してcrossが正本unreachableなら、同じcomponentには居られない。別component間には最初の隣接辺が無いためjump/goal占有が不可能。双方own-goal reachableなら、ds<=doでSTM、do<dsで相手が最短ordinary手のraceを勝つ。real W/Lには別のhistory資格が要る。

追加は既存pairの高々2cross u8 reads/branchで、新保存/BFSは0。ただしpair missingやwrong keyをsentinelにしてはいけない。Bのroot3は両cross有限の別componentで、signatureだけでは検出しない。ID版の1/33をcheap signature版の件数にしない。完全component mapはwallごとfloodとowner/寿命が別なので、今は保留する。

## 4. fixed winning policyに対するfuture-phase E

Pを普通に進むsimple/strict rank方策は、将来joint board/turn keyを各一回しか訪問しない。wが同じセルに留まる相手手前後もturnが違う。したがってinitial Eの全projected keyが、方策の未来Qと非交差ならthird arrivalは無い。

- δ=0：Q={v1..v_(n-1)}×両turn。
- δ=1：これに(v0,w手番)を足す。
- current key自身は将来再訪されず、vnはgoal-firstで終わるので除ける。

これはB6を取り入れた精密化で、初稿のv0/goalも含む保守的maskの十分性を否定するものではない。geometryで証明したwitnessとEで検査するrouteを同じにする。適応DAGなら全採用方策を覆うmask等が必要。restricted chamberならglobal D_wではなくそのrestricted policy自身のrankを使う。

base1+overlay1はcount2。完全正本E/aggregateを保ち、from_countsの完全性をgeometryで作らない。current historyやTT keyをQへ置換する話でもない。2phase masksとgeometry成功後のscanが必要で、O(H)と呼べるかは既存count/iterator費による。H entriesにO(H) countを呼べば二乗になり得るが、現APIがそうだと認定したわけではない。new clone/map/別count ownerは作らない。

## 優先4案と最小の次検証

| 順 | 候補 | 必要な情報と費用 | 最小の次確認（計画のみ） |
| --- | --- | --- | --- |
| F1 | 一本time path＋parity split | 既存qualified2 maps/edge情報、O(n) pawn依存走査、geometry成功後history/TT費 | B事前固定171への新parity述語だけ一回、初稿8述語/solver再演なし。Aはdispatchしない |
| F2 | legal goal＋標準ds1 terminal-tail | ds/少数local辺、E又はK1/K2 canonical counts。key/make/undo費別 | sealed endpoint/上下反転/side-open/N>=3と二中間history trap。新補題だけ |
| F3 | cross sentinel component race | 高々2cross reads、new metadata0 | own finite/sentinel/wrong-keyとroot3 finite別componentを方法別に分ける |
| F4 | 同じwitnessのfutureQ/E資格 | O(n)maskと正本aggregate scan、API費未知 | currentcount2、δ1初到着、goal優先、weighted合算、別route不一致を拒否する境界 |

F1のDAG/exactrho/gateは追加coverage・償却の証拠がある場合だけ比較する。F2を長いcorridor一般式へ拡大しない。F4は幾何勝ちそのものを増やすfamilyではなくhistory資格である。どの候補もzero-stock endgameの案で、現在openingの費用問題を直す証拠ではない。

A4/B5一般corridor、A6安い閉じたnon-loss集合の発見、A5landmark/allpairsは優先から外した。数学が偽という扱いではなく、具体例/全応手証明/費用が未支持という判断である。旧424 selector/counter/cacheを戻さず、two-speedだけのpath案を別familyへ数えない。single D-safe traceや最短DAG非交差だけからDraw/nonDrawを作らない。

## 証拠の強さ、相互確認と未解決

条件付きで独立に論証したのは、基本time、B提案のparity split、標準ds1 tail、component race/cross sentinel、fixed-policy futureQ、G1/G2 gateである。型/consumer/source/softwareのclearではない。Aのsealed-tail forcedDraw帰結と、正しく束縛されたboard non-lossのhistory保存への補足は、B最終の明示確認をまだ見ていない範囲として分ける。

B初稿の1368 checks/164 BFS/13 Tarjan、9x9 33幾何通過、small W/L+Draw不一致0はBの固定資料として参照し、Aは再演していない。終盤/二共有familyの偏り、canonical E/actual proofleaf UNKNOWNを保持する。Bの今後のparity/tail有限結果も、実際に報告された分だけであり、Aが代わりに実行済みとはしない。

AのStage3では新しい色4caseと上下goalの標準wall-span2caseだけを一度計算した。これは整数整合で、board WDL/current native historyやsource資格を確認したのではない。Stage1の6、Stage2の1、Stage3の6でA累積13/4096 checks、BFS0/512、明示manual board5/16。成功確認・元solver・Bのcensus再演0。B担当の予算と混ぜたりphaseでresetしたりしない。

未知は、実visited node分布、history適用率、現在count/projection API、追加metadataの償却、predicate費込みwhole速度、棋力、採用、LLM/管理総費・連続family peak。新しい実験・source・観測/cacheを発行せず、追加ラウンド/第三担当も自動作成しない。重要な新定理は実際の相互確認の範囲だけを統合324が扱う。

## 引渡しと停止

初稿initial.md/jsonとStage2 peer-b-critique.md/jsonは不変。新しいfinal.md/jsonにこの一度の改訂を保存し、元参照・限定Ruff/Prettier・必要算術・実source/helper/formatter STOP、directwait/reap・fresh PID-start-boot・handles/TMP/leases/owned[]、新Stage3 affected使用と通常Beads backupを結ぶ。

本人428.1だけを検証close/showclosed/backupし、final packetを通常wrapperで統合324/thread01a1376a/issue428へ一度返す。Bは必要範囲を読んで自分の最終版と比較要約を同じ324へ送る。親428/324・Main/Git/Cargo・B leafは変更せず、Root/人間ACKや新しい議論phaseを待たない。USERPAUSE/defaults/models/weights/seals/oldfits96/foreign・全RAWFAILED費UNKNOWNは不変である。
