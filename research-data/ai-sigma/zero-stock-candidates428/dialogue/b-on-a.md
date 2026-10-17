# B から A 初稿への批判（Stage2、ここで固定）

対象は A の initial.md SHA256 `7d551c1ab874fde70cfb761ce724c4c721e81ce01af2f9d6af0326b1f27155d8` / initial.json SHA256 `8e35f6209da03950eaf0bff1fab4464f6609915e1f1872fac0629a3e64ba12be`。自分の初稿は先に固定した。A の Stage1 completed event、public final、stage1-STOP、自然 idle を確認してから Stage2 を一度だけ配送した。turn/start accepted の receipt は a-stage2-delivery.json。A の途中の推論や未完成 draft を読んで案を合わせていない。

七方法族すべてを検討した。新しい numerical predicate/BFS/solver はこの Stage2 では 0、累積は 1,368 checks / 164 BFS のまま。自分の初稿で得た固定保存照合は再実行していない。以下の「確認」は明記した条件に関する数学的検討であり、current consumer software、canonical history、速度の受入れではない。

## A3：時刻式は独立に同じ結論、gate の等式には資格を明記する

**維持、最優先。** A の中間式と δ=1 の v0 式は B3 と同じ条件になる。相手の t 手目直前の winner の点を `v_(t-δ)` と書くと、最初の jump の存在から `dist(b,v_(t-δ)) <= t` が従う。A3 の strict inequality はこれを除く。winner の i 手目の target 占有には相手の `i-1+δ` 普通手しか使えず、中間点ではより強い式、終点では別の `>n-1+δ` が占有を除く。相手の goal 先着も `d_q>n-1+δ` で別に排除される。相手が shortest DAG の外へ detour する場合も、普通距離の下界なのでこの帰納に含む。side jump は着地が斜めでも、踏み越す pawn への普通隣接辺が必要である。

「相手の手後の隣接は許す」という説明も正しい。隣接した直後に相手がもう一度指すわけではない。winner が次の空の target へ進んだ後、その**新しい** winner 位置に対する相手手前 guard を課す。盤外への直進は path の合法普通辺の検証で除外し、endpoint の占有は別に必要となる。

gate の `dist(b,v_i)=dist(b,c)+(i-t)` は、c が b と suffix 全点を分離し、suffix の長さ `i-t` が G 全体での c→v_i の geodesic であることから初めて従う。全体 P が普通の最短路なら subpath も geodesic なので、A の前提から導ける。単なる「その通路内での最短」へ移すと等式をそのまま使えない。複数入口、c が goal、相手が既に領域内、a=c の各分岐を explicit guard にすることを勧める。条件違いの B4 protected chamber の式を、この gate 等式へ無条件で混ぜない。

費用上は「旧 L が安く失敗した」という保存観測に対し、一本 path でも各 UNKNOWN node に最大4nの edge/gradient 検査と点ごとの下界が増える。B の固定9x9では33/33幾何通過だったが、二共有 family の終盤標本であり、元約260万内部判定の利益分布ではない。DAG、exact rho、gate の追加 metadata はそれぞれの追加 coverage が必要で、全部を一度に実装する根拠は無い。今回の固定集合では B3 の一本/DAG、reuse/rho は一致した。

**追加の精密化の問い。** 初稿固定後、A を読む前に [stage2-independent-note.md](stage2-independent-note.md) に書いた格子 parity が使える。初期色差 p と δ が等しい場合だけ、相手の first jump があり得る。異なる場合だけ winner の次 target の通常占有があり得る。従って「first jump だけを除く場合は endpoint occupancy 式を省く」「jump が parity で不可能なら target ごとの `ell(v_i)>i-1+δ` だけにする」という弱化候補がある。これは A3 が不正という指摘ではなく、同じ方法族の guard を弱める未照合の候補である。実座標 parity を用い、goal-distance 差自体の parity が正しいとは仮定しない。Stage3 で独立に成立/反例を判断してほしい。

## A1：即時 goal は維持、二手 L は三つの子終了を区別する

**維持、優先度高。** canonical legal goal 手は history-independent な W。二手 L には「自分の即時 goal が一つもない」「全自手の子が既に threefold Draw にならない」「全てに相手の実 legal goal 応手」が必要であり、A はこれを述べている。ordinary ds/do の比較や壁距離だけから二手 L を返さない点を維持する。実装時には普段の legal generation/terminal/enter/undo/control と二重仕事を作らない位置が必要で、最大約25枝は無料ではない。

E2 は「ds=1 が即時 legal goal を保証しない」正しい反例だが、board-W 自体への反例とはまだ言えない。標準の長さ2壁と合法 own-goal 到達性を使うと、手番側 ds=1 の全例を高々3 plyで勝ちにできる可能性がある。goal y が相手に占有され、横の side goal landing が全部閉じると、yの横辺を塞ぐV壁は直上xの横辺も塞ぐ。yはdegree1、合法な相手goal到達性によりxの後方zは開く。`x→z, y→x, z→y(goal jump)` が成立する。上下反転も同じ。E空または二つの中間到着の正確な履歴資格は別に要る。

これは任意の synthetic graph には拡張できない新しい補題候補で、A1 を誤りとするものではない。A の E2 の 9x9 corner はまさにこの退避で勝つ有限 pattern になり得る。追加 lookup は既読 ds と局所壁程度で済む可能性があり、corridor 一般式より先に反証する価値がある。Stage3でこの geometry 論証を独立に検討してほしい。

## A2：cheap sentinel は健全、有限 signature の逆は使わない

**維持、優先度中〜高。** 正しい own value が有限のときの cross unreachable は別成分を証明する。sentinel を finite gap に混ぜず、missing cache と unreachable を分ける説明も正しい。両 cross が有限でも別成分となり得るので、これで取り逃すのは許される。B の427 root3は両 cross が有限な別成分で、完全 ID が必要な具体例である。

成分 ID を作るなら「wall ごとに一度」と書くだけでは足りず、その owner が同じ wall key に何 node 再利用されるか、positive-stock sibling の wall 変更で破棄するかを詰める必要がある。qualified pair の単一 invocation scratch へ追加する場合と、accumulator の共有 geometry に追加する場合は保守費が異なる。新しい global cache を正当化するほどの頻度は今回不明。初期は cross sentinel だけを候補とし、完全 ID は費用未支持のままでよい。

## A4：通路の一般式は未証明として維持

**未証明、優先度低。** 手番と ordinary 差だけで corridor W/L を返す式は提示されておらず、これは健全な留保である。全合法退避/追従/side jump/枝退出を受けた rank と policy の両方が必要。「唯一の通路だから互いに前進する」は誤りになる。goal が chain の中間にある場合、端点での占有、曲がり角では straight landing と側方 landing の関係も変わる。

上の A1 の terminal-tail のような有限 pattern は具体的に証明できるが、それを長い chain 全体への一般 macro と数えない。wall preprocessing、transfer table の生成、境界条件の保守が重くなる案は、局所 terminal predecessor より先に作らない。今回新 solver/pattern registry を発行しないという境界を維持する。

## A5：sound な既知方向、次の重点にはしない

**維持するのは数学の位置付けだけ、優先度低。** 正確な landmark 差が ordinary rho の下界となること、旧 T に届けば旧証明が使えることは健全である。しかし427の9x9有限失敗12件は L=rho<T なので、それらには改善不能。kN情報量、k BFS または pawn BFS の費用が増える方向であり、414/424の撤去を戻す理由にはならない。

all-pairs 6561Bは距離の情報量だけで、key、cache owner、alignment、clone、miss構築費を含まない。既に全域表が存在するときの query と、今回のために新たに構築する場合を分ける A の留保を維持する。小盤面での追加例を時間利益へ外挿しない。

## A6：両者 non-loss の論理はよいが、安い証明発見が未解決

**条件付き論理を維持、安い cutoff の候補としては未証明/優先度低。** p 自手では少なくとも一つ、相手手では全ての合法出口に p 非敗戦があるという閉条件は、相手 goal を排除する policy を与える。正規ルールの有限状態で終端を避け続ければ joint board/turn が反復し、自動 threefold は draw なので p は負けない。早い履歴 draw も非敗戦を壊さない。両 p の非敗戦が独立に成立して初めて Draw、片側だけで Draw にしない区別は正しい。

出口の「既証明 p非敗戦」は同じルール/手番/score/history domain の証拠でなければならない。保存の単一 D-safe trace、history-free W/D ラベルだけを current fullhistory の無条件出口として借りない。own goal は非敗戦出口として明記し、opponent goal は必ず拒否する。

最大の未解決は小さい S の発見と全 off-cycle 出口の資格で、K<=8 と置いても安く閉じる実例は無い。二つの policy が別々の history count map を所有する必要はなく、完全 canonical context を共有して正規終端を処理すればよい。現行 SafeRaceLeaf は terminal utility の ±値だけを資格付けており、片側 non-loss bound や Draw を同じ leaf として入れる変更は別の型/namespace設計である。今回その拡張を認定しない。

## A7：履歴緩和は健全、未来 phase を使うと過剰拒否を減らせる

**維持、優先度中〜高。** 固定した勝ち方策が simple route/strict rank を進み、同じ joint key を再訪しないという論証は、turn を key に含めれば成立する。E の winner-cell が path cell と全て非交差なら、過去count2への到着を避ける。weighted base + overlay の合算、完全 E の scan、適応的 path 切替の再資格を保持する点も正しい。

A7の v0 を含む全path mask は十分条件として安全だが、δ=0 の v0 や真の終端 goal を含めることは過剰拒否となる。B6の future `(winner-cell,turn)` mask は、δ=0ならv1..v_(n-1)×両turn、δ=1ならさらに(v0,wturn)を加える。current key 自身は将来再訪されず、goalはtrue terminalが優先する。交わる key があれば UNKNOWNへ戻すので、相手位置を省く緩和を誤って無条件にしない。

phase maskへの追加費と救える実例数は不明なので、A7の単純cellmaskを捨てる必然はまだ無い。B4のrestricted routeでは global Dw が減らない場合もあるため、同一 key 非再訪の根拠にはそのpolicy自身のsimple path/rankを使う。canonical APIへの差込・weighted E境界・TT fullhistoryの確認が済むまで実WDL/coverageに昇格しない。

## 統合に渡す優先順位

A3の一本+既存map、A1の即時goal/小さいterminal-tail、A2の既存sentinel、A7のpolicy-local E を先に比較する。A3のparity弱化とA1の距離1補題は新しい小さい検証対象で、現時点で両者合意や採用としない。A4/A5/A6の一般形は、費用と具体例が無いという未解決を残す。新しい第三者レビューや次ラウンドを自動発行せず、この批判に対するAの一度の最終改訂を受け取る。
