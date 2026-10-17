# 428.1 A：固定B初稿へのStage2批判

B1〜B6の六方法族を全件検討した。Bの望む結論へ合わせることを目的とせず、条件付き数学、実装に足りない前提、費用、保存照合の範囲を分けた。Aの初稿は変更していない。

結論として、B1/B2/B3/B4/B6の**記載された条件付き論理**は支持できる。B3には名称の具体的な過大表現があり、B4/B6には所有/計算量の追加資格が要る。B5一般macroは未証明のまま。今回、現在のB3/B4式そのものの誤WDL反例は見つけていないが、Bの全保存照合・実行sourceを独立再認定したという意味ではない。

| peer ID | 判定 | 重要な修正・不足 | 検証優先度 |
| --- | --- | --- | --- |
| B1 terminal predecessor | 維持 | 子threefoldと全初手、既存terminal/score/enter/undoとの仕事重複 | P2：既存legal情報があるなら即時goalから |
| B2 component | 維持 | exact IDとcheap signatureの件数を分ける。signature同一は同componentでない | P2：cross signature、ID前処理はP3以下 |
| B3 timed route | 条件式は維持、名称修正 | contact自体は許す。初手/各phase/endpointの式を混ぜない | P1：既存表＋一本。DAG/exactrhoはP3 |
| B4 chamber | 定理維持、所有/費用を追加資格 | restricted path/key、全入口、per-gate BFSと保存寿命 | P3：metadataが既に使える場合に限る |
| B5 corridor macro | 一般式は未証明 | true degree2の局所jumpは単純化できるが、敵の退却と全出口は残る | P4：局所lemma/具体例まで |
| B6 policy-local E | 固定方策Qは維持、API/計算量を追加資格 | witness一致、aggregate count、projection抽出、scanがO(H)の前提 | P2：native APIと拒否分母が必要 |

これらは未来の比較/確認を優先付けたもので、source役・実装・Search・新性能測定の発行ではない。

## B3：式は成立するが「contactなし」ではない

wのpathをv0..vn、w後手ならδ=1、先手なら0。混同を避け、ここではBの相手goal距離mをd_q、w到着前の相手手数をr=n-1+δと書く。Bの条件は

- d_q>r。
- 0<=j<nでell(vj)>j+δ。
- ell(vn)>r。

wのi手目前にqはi-1+δ手済み。i<nの中間条件、又はi=nのendpoint条件から、wが着地したい点はqに占有されない。従ってwは指定ordinary手を合法に選べる。

qのt手目が最初のjumpと仮定すると、その直前にwはv_(t-δ)に居る。qの過去はt-1普通手なので、wへの隣接辺を足してdist_G(b,v_(t-δ))<=t。中間条件ell(v_(t-δ))>tと矛盾する。δ=1,t=1がv0の初期非隣接を処理し、δ=0ではq最初の手の前にwがv1へ動く。straight/sideの双方がこの最初の隣接を要する。最後のw着地後はgoalで終わり、qの次手は無い。qはr普通手でd_qへ先着できない。

この証明には各ell(v)が正しい到達下界であれば足り、下界関数全体のLipschitz性を余計な条件にはしない。旧root閾値との包含を示す場面や、別の圧縮案に三角不等式を使う場面とは区別する。δ=0,d_q=nのtieはw先着、δ=1,d_q=nは相手先着なので拒否となる。中間ell=j+δの等号では最初のjumpを否定できない。strict式は十分条件として維持し、等号を落とせば常に負けるという必要条件の主張はしない。

### 名称を反証する固定境界E5

wall-free9x9、w=(4,6)→goal y8、q=(4,5)→goal y0、w手番。Pは(4,6),(4,7),(4,8)。Manhattan ellは[1,2,3]、n2、r1、d_q5でB3条件を通る。

開始時から駒は隣接している。wが(4,7)へ動いた後、qは(4,6)へ普通手を指せる。このq手の後にも隣接するが、wは空の(4,8)へ普通に着地してgoalとなる。qが動く**直前**には距離2でありjumpはできない。

従ってB3は「全てのcontactを禁止する」述語ではない。名称は「最初の相手jump・指定route占有を排除する経路」等へ直すべきで、実装でq手後の隣接まで余計に禁じない。これはB3の誤WDL反例ではなく、名称/phaseの誤読に対する反例である。標準初期から20壁消費の実stock0 prefixやE資格はUNKNOWNで、正規対局の新事実にはしない。

この1例だけを事前固定し、新しいManhattan算術・B3条件を一度確認した。Stage1の6件やBの171状態は再演していない。A累積は保守的7 checks/4096、BFS0/512、明示境界5/16。

終点占有はB1のsidejumpで勝てることもあるが、B3は指定ordinary policyの証明なのでendpoint式を無根拠に削除しない。δ=1のv0式を省くと相手が最初にjumpする例があることはA初稿E3で示しており、ここでは再計算していない。

## B4：gateへの最後の到着は許せる

SをG-gの成分、a∈S、bはS外かつgでないとする。候補goalとwの全ordinary pathはS内である。qがSへ初めて入る、又はS内wへ初めてjumpするには、その前にgへ居る必要がある。Sと外の隣接を結ぶ頂点がg以外にあれば、そもそもG-gのcomponentという前提が崩れる。

w到着前のq手数をr=n-1+δとする。qのt<=r手目に初jumpするなら、それまでのt-1普通手でgへ到達しているためdist(b,g)<=t-1<r<=Hとなり矛盾する。H=rで、qが最後のordinary手に初めてgへ来ること自体はよい。wの次点/goalはS内でgではなく、もうqは動けない。ordinary進入もg到着後にもう一手要る。よってH>=rという非strictの式を支持する。

Hをr-1へ緩めると、qが最後の手の前からgに立ち、S内に隣接するwをjumpできる余地が開く。これが直ちに全局面で負けという意味ではないが、現証明では除外できない。goalをgへ置く、wがgを横断する、別入口を省く場合も同じ証明は使えない。複数入口は全てを覆い、minの早着側で判定する。

Bは既に「S内pathをglobal Dwで代用しない」と明記しており、ここは正しい。さらに実装時には、restricted mapsはG-gという別のgraph上の情報なので、full-Gの既存pairと同H/Vだからと混ぜない。gate identity、寸法/goal方向、除外頂点、wall keyと借用寿命が資格になる。

費用はTarjan一回だけでは済まない。各選択gateのcomponent情報、2restricted goal maps、optional gate-distance mapの形成/保持が別。K gateならその分のflood/BFS仕事が増える。概念上324B/gateは情報量であって、allocator/key/padding/複数wall-key/既存scratch owner拡張やRSSの総費ではない。既存qualified metadata無しにO(K) queryだけを安いと宣伝しない。B3の一本が既存pairだけで済むなら、chamber新metadataを先に実装する理由はまだ無い。

## B1/B2：正しい基準でも無料ではない

**B1。** legal goal手があるならgoal-firstで一手W。全自手の後で相手goal手が必ずあり、子が既に自goal/threefoldDraw等で終わらないなら二手Lでよい。相手の返手を普通最短と決め打ちしないことも適切である。だが<=5×5のlegal生成だけでなく、全子のmake/terminal/history/control/undo費を含む。既存Searchはほぼ同じ即時枝を調べるので、二手predicateが安いとはまだ言えない。現在safe-race位置にlegal maskが無料であることも未確認。数学W/Lから独自のnumeric/mate値を作らず、既存score domain/leaf kindを保つ必要がある。

**B2。** 別componentなら最初の隣接辺自体が無く、straight/side jumpやgoal占有が起こらない。own-goal reachableなら各自の最短ordinary raceでboard winnerは決まる。finite signature差もこの分離を証明するが、同じsignatureの別componentは検出しない。

B記述のroot3は両cross有限なのでsignature版では救えない。従って表のB2=1/33というcomponent-ID版の件数をcheap signature版の成果へ移してはいけない。ここはBも事実を明記しているが、最終比較で方法の分母を分けるべき点である。signatureは既存表の高々2read、ID版は新floodと約N IDの別案。同じ壁のpawn差ならreuseできる一方、別wall-keyや異なる寸法へ持ち越せない。metadata miss時fallbackは正しく、恒久cache owner追加は未正当化のままとする。

## B5：局所jumpと一般WDLを切り分ける

Bの16/21例は、記載されたdegree/辺を前提とすれば、P0の退避16→11、P1の強制21→16、P0の11→21 goal jumpという短い方策として理解できる。元V bitsのgeometryやhelperは再実行していない。中間子のprior count2ならそこでDrawになるため、E条件又は個別canonical履歴確認を省けない。

一つの局所lemmaは簡単にできる。占有された内点vの**global wall graphでの真のdegreeが2**、その隣がu,t、uに動く側の駒、vに相手、tが空なら、u→tのjumpは合法である。

- u-v-tが一直線ならstraight landing tが開いている。
- 曲がり角ならvのstraight奥は第三の辺なので閉じており、開いたv-tへsidejumpできる。

従って曲がり角だけでtransferを除外する必要はない。ただし「局所部分graph内でdegree2」にすり替えると、外のstraight辺が開いてsidejumpが禁止される反例ができる。branch/出口を全graphで資格付ける必要がある。このlemmaは旧suite/solverを使わない二場合のルール論証で、一般corridor勝者公式を与えたものではない。

相手の後退、oscillation、goal途中/端の占有、入口からの退出を含む全応手のrank/terminal treeが無い限り、一般macroはUNKNOWNで維持する。transfer構築や保存量を未確定のまま安いlookupと呼ばず、各wall layoutの二駒tablebase/solverへ広げない。B1三手拡張と同じ16/21例を追加coverageへ二重計数しない点は適切である。

## B6：futureQは支持するがnative complexityは未確認

固定strict-gradient pathなら、wのセルは各自手で進み、同じセルを保持する前後もturnが違う。将来の同じjoint HistoryKeyは一回なので、initial Eのkeyにその方策が到着しなければthird arrivalは無い。

BのQはδ=0でv1..v_(n-1)×両turn、δ=1でさらに(v0,w手番)。現在key自身とgoal終端を除ける添字は正しい。δ=1の最初のq手後はv0,w手番なので含む。goalはhistoryより先に終了する。A初稿の全セルを含む保守的maskより細い条件として理解できるが、A初稿はStage3まで改訂しない。

幾何が証明したpath Pと、Eで調べたpath Qが異なると破綻する。例えばEがPだけにあるセルの到着keyをcount2で持つのに、別safe pathのmaskだけで通してPを実行すればDrawを見落とす。適応DAGなら全採用方策を覆うmask、又はhistoryを通った同じ固定witnessへ方策を固定する必要がある。Bもこの注意を書いており、実装時の重要境界として維持する。

canonical base1+overlay1はcount2である。raw weight個別判定、synthetic flag、最後の壁というshortcutは使わない。既存key ownerからpawn/turnを定数で投影できるか、aggregate iteratorがあるかは未読。O(H) scanは各canonical countが定数/償却定数のときの条件付き費用で、H entriesそれぞれにO(H) countを呼べばO(H²)となり得る。これは現実装が二乗だと認定したものではなく、API未確認の費用上界を勝手に線形としない指摘である。

path形成と2u128 masksの費用、geometry成功後のscan/TT store増も含め、既存E空fast pathを保つ。新clone/history map/別aggregate ownerを各nodeで作らない。fullhistory/typed TT key/domain/methodを残す。現在Eの実通過分母が未観測なので、救える件数/whole利益はUNKNOWNである。

## 保存証拠と残る問い

Bの固定初稿が報告した1368 checks/164 BFS/13 Tarjanは、今回再演していない。171=161+2+8、1368=8×171、58+20−16=62という記述内算術は整合する。B3の9x9 33通過、DAG/exactrho追加0はその偏った固定幾何集合の説明であり、canonical E/actual proofleaf/独立9x9 WDLや性能を確定しない。small W/L128+Draw2の保存不一致0も一般安全性の代用にしない。

同じ集合でDAGやexactrhoが追加0だった以上、今その費用を払う根拠は無いが、全boardで同じpredicateだと一般化もしない。Python子0.009626sはguardianに内包され、Rust実装predicate、whole速度、棋力の測定ではない。

Bに返す問いは、B3の名称とphaseの修正、B4等号/restricted key、B2二実現の件数分離、B6 witness/API complexity、B5局所lemmaとgeneral未証明の分離。これらを反映した一度のStage3改訂へ進める。新議論ラウンド・第三担当・source/observer/cache/科学jobは作らない。

このStage2のwriteはA namespaceだけ、Main/Git/Cargo/モデル/forward/Search/solver/fit/game0。Stage1成功確認の再実行0。scope限定Ruff/Prettier、exact peer refs、累積予算、実helper/readers/formatter/directwait-reap/fresh PID-start-boot/handles/TMP/leases/owned STOPを保存し、routing-handoffに従って統合324へ一度返して自然idleとする。428.1はin_progressのまま、Stage3の一度の自己改訂前にcloseしない。全USERPAUSE/defaults/models/seals/RAWFAILED費UNKNOWNは不変。
