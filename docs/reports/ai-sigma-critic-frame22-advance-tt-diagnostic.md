# frame22 advance内部費と合法sequence TT機会 / quoridor-4lc.277

最初の科学診断は不成立として保持し、統括が同総予算内で明示配分したprospective MAX2修復で、503実子のadvance内部費を有限測定できた。両goal wall-map再構築は包摂advance費の66.73%を占め、次の介入候補をここへ移す根拠になった。TTはinitialの完成depth2／短いPVのため手跨ぎ候補が未記録で、再利用利益は未確認。旧失敗を成功へ置き換えていない。

旧275はclosedのまま、NN243500・processed1566984・旧費と失敗を変更していない。275比較4sourceの基準は9d7e02d1d69ee47817a2f4a38ce259774624c799、主保存証拠は209de5bd7eb1eeee3fd3781bd7b35b13d7720822。主モデルや学習・教師生成条件は変更せず、比較WT内の私有診断だけを追加した。

## 予定と実行

Beads本人claimは13:05:21 UTC、静的準備を開始。273生成停止と274 B優先の13:15までの予約を保持し、B-r1・selection-r1のwait／exactidentity不在を本人readで束縛した。計算直前のloaded state、正monitor-process、24入力hash、config/contract、PID-starttick、実foreign CPU、RAMと保存は各admissionに記録した。LLMの人数／activeだけを拒否理由にしていない。

私有cfg(test)計時で4保存prefix（initial、opening、walled-midgame、jump-p2）の全合法子503件を観察する予定だった。owned deltaを使い、275の追加scratchを有効にしない。encode内部のmap cachehit／両goal map構築／sorted IDs／STM距離取得、親・特徴検査／値clone／ID差分＋FT更新を排他spanとし、advance全体は包摂、evaluateは別spanと登録した。FTのID差分検出と加算自体は分けて計時していない。map構築にedge確認・whole-map materializationを含む。各span計測・observerの残余を独立したアルゴリズム費とはしない。

TT診断はinitial/P1とjump-p2/P2、旧root最大depth3／node2500から保存完成PVの1手後・2手後を使う予定だった。Tableを観察するだけで新探索へ渡さず、full state／反復count／total ply／synthetic／bound／depthを保持。モデルfingerprintとschemaは外側に束縛する。現Keyにmodel世代は含まれず、searchごとにTableを破棄する現仕様ではモデルが不変であることに依存する。常設TTには別の世代無効化が必要になる。

## 診断失敗と有限訂正

科学jobは13:18:42.381269–13:18:42.598053、0.216800589秒、exit1、全wait／現在exactidentity不在。NNUE私有testはexit0、AI私有testはexit101。元sourceはfailed-science-source.tar.xz、元登録・stdout/stderr・process・advance-result.jsonの原PASS表示は保存し、failure-and-invalidation.jsonで明示的に不認定にした。

原因は診断側でimmutable APIの戻り値を無視したこと。SigmaContext::play(&self, id)は新contextを返すが、観察器はchild.play(action)の戻り値を保持しなかった。その結果、503件すべて親を評価し、cachehit503／build0や子parityを誤ってPASSと表示した。この時間値、cost比、cache件数、子数値parityは次の最適化順位へ使用しない。モデル評価が実行された事実の1006NNは保持する。

AI側は最初の旧root探索後に completed_depth>=2 && pv.len()>=2 が成立しなかった。各項の実値とTableが保存される前にassertionが発火したため、NO_COMPLETED_DEPTHやTT一致なしとは判定できない。旧root探索の実NN／processedはUNKNOWN、source・node上限から各2500以下。合計NNはknown1006＋UNKNOWN上界2500、保守charge3506。planned science上界10006／NNcap12000、processed予定上界9000／cap32000を変更していない。TT全2rootと全4移行予定の未確認分母を保持し、成功の補充は行わなかった。

訂正sourceでは child = parent.play(action)、next = next.play(action) とし、ply増加・position差・親不変を明示検査する。短い完成PVはtyped missingで保存する。科学版と訂正版は別archive／SHAで保持し、訂正版での性能・NNUE子parity・TT機会の再実測はNOT_RUN。

NN0のcursor contract testだけをcompile＋必要test60秒枠内で実行した。503全合法子、うちwall変更489／非変更14、P1/P2、正常context、ply+1、親fullkey不変はPASS。これはsource経路上では489回のmap再構築と14回のcache再用を予想させるが、実費の大小は未測定である。共有RuleAによる検査であり、独立した全deep合法truthではない。元計時の救済や新forwardには使わない。

整形済み訂正sourceのRustfmt check、Clippy -D warnings（AI/NNUE lib/tests）、Python Ruff format/checkはPASS。compile21.291901秒＋NN0cursor test9.614112秒＋lint3.952778秒＝34.858790秒／60秒。NN0testにモデルload・search・forwardは含めていない。全scienceはMAX1／30秒内、追加jobなし。管理オーケストレーションのJS構文失敗2件はnested tool実行前で0科学／0NN、科学損失に付け替えない。

## 次判断と保存境界

修復配分前の次案は訂正観察器の再診断だった。この有限修復を統括が明示採用した。以下の元失敗・当時の不足は保持し、修復後の次案と支持範囲は末尾に別記する。489件のwall変更という有限検査はwholemap生成の観測価値を示すが、ID生成・更新との費用順は未確定。現root_depthはTTを値／orderingに参照せず、通常同engineの次手番は2ply後。完了depth2から2ply先にはdepth0しか残らず、部分depth3で有効なentryが残るかは未記録である。within-search97hit／0cutを手跨ぎTT方式一般の棄却へ広げない。

次の訂正診断は、必要test／計算／保存を今回実費に近い短枠で見積もれるが、成功や同じhost費を保証しない。主273 GPU教師生成と274学習をこの不足で止めない。全MCTS生成倍率、教師品質、同時間棋力、最高目標達成は本課題の主張外。

新scope1MiBは旧2758MiBの確認unusedから移転、旧retain7MiB＋新1MiBで総予約を増やさない。shared release増分16MiB枠内、既WT8MiB内、旧unknown128MiBを保持。新取得・削除・Git/index操作は行っていない。現sourceは比較専用でありmain採用なし。全attempt、元科学source、訂正source、入力／モデル参照、process、失敗、不認定理由、保存／復元receiptを当scopeへ小保存して統括へ引き渡す。最高goalは未達。

## 明示配分による同予算修復v2

統括は原slot1／失敗／費／charge3506を受け入れ、同277へprospective MAX2の一回修復を明示配分した。科学30秒、compile/test60秒、NN12000、processed32000は不増。4fixture503actualchildrenは元1006NN、TTはfirst fixed initial一rootだけ（old2500＋freshdepth1最大1000×2）で登録し、最大新5506NN／累積9012、短PVはtyped missingとした。第二rootの再run、深さ／node補充、最適化、モデル・数学・鍵・ordering変更は行っていない。登録preregister-v2.jsonとscience-r2/admission.jsonが版・目的・source／controller／model・現在物理を束縛する。

再build前にmain cwdでguardを呼んだ管理入口はprivate-WT assertionでchild前に停止し、compile-r2-prestart-error.jsonへ保持した。build／science／NNは0。原因を特定して正しいmanagedWTからcompile-r2aを実行し、18.681302秒で成功。追加Clippyは1.205089秒で成功。全compile／NN0test／lintは54.745182秒／60秒で、元費を引いたまま収めている。

科学r2は13:29:18.438303–13:29:18.657549、0.219282647秒、exit0、全子wait／現在exactidentity不在。private AI binaryのfilterにはcursor NN0検査も含まれ、これをforward件数へ加算していない。実3229NN＝advance1006＋TT2223、processed2500。旧UNKNOWN上界を保持した累積chargeはNN6735／12000、processed上界5000／32000、科学2job合計0.436083236秒／30秒。

| 503実子でのspan                | 合計ns | 包摂advanceに対する割合 |
| ------------------------------ | -----: | ----------------------: |
| 両goal wall-map再構築（489回） | 518499 |                66.7337% |
| sorted IDs生成                 |  80923 |                10.4152% |
| IDs差分＋FT更新＋finite検査    |  55240 |                 7.1097% |
| 親／features検査               |  39074 |                 5.0290% |
| 値Vec clone                    |  11362 |                 1.4624% |
| STM距離lookup                  |   7190 |                 0.9254% |
| map cachehit（14回）           |    277 |                 0.0357% |
| observer／未計時の残余         |  64402 |                 8.2889% |

advance包摂は776967ns、evaluate別spanは289011ns。排他spanをadvanceへ再加算しない。map構築割合は4fixtureそれぞれ64.878–67.567%だった。503actualchildrenのfeaturesはfull構築と同一、full／delta値の最大絶対差は1.1920928955078125e-7、344件はvalue bitが異なり登録tolerance内だった。bit完全一致とは認定しない。親不変・正常context・ply+1・盤面変化を検査した。shared encoder／RuleA依存の有限parityであり、独立教師truthではない。

TTの実初rootは2500node、2223NN、completeddepth2、Action148、PV[148]、8hit／0cut、retained261entry。登録した機械条件によりNOT_RECORDED_SHORT_COMPLETED_PVとなり、1／2plyの鍵／usable-depth対応は観察していない。このPASSは診断testの実行成功を意味し、TT機会・fresh同horizon値／Actionの支持ではない。原slot1の実値は保存前に失われており、このr2実値を原slotへ補填しない。全rootplanned2から修復1へprospectively縮小した区別も保持する。

次最大1は **NNUEの両goal whole81 distance map構築をu128 frontierで問う介入**。現coreのshortest-only経路の既利益を移植するのではなく、blocked-edge mask作成、両goal層展開、81距離materialization、Arc/cachecaller費を含めて比較する。実装の目安はfeatures私有builderとoracle testの数KiB、同一503子×81距離と盤端／wall／到達／P2をfixedqueue oracleで確認し、Scalar／Simd full-deltaと同depth／nodes／値／Action／root復帰を別に検証する。必要build/testは約60秒、科学は元診断相当の小NN枠と数秒、保存1MiB程度を次具体契約の上界候補として返す。見積もりであって現277の追加実行許可や速度保証ではない。今回は実装しない。

このrootchild群はwall変更489／503という分布であり、全searchのcaller分布とは異なる。66.73%を旧275のadvance比へ掛けてwhole速度倍率にしない。1観察sample・microtimer／coldwarm／cache／host差の不確かさを保持する。現MCTSは別入力経路・推論API99.1%の有限所見があり、本NNUE内部費を全教師倍率へ変換しない。手跨ぎTTはfullhistory／同engine2ply／root未読／model世代／残深さ／boundsの問いとして保留し、NNUE幅や実caller分布が変われば優先順位を再検討する。
