# 151 StageB全16保存局の独立有限裁定 — 155

2026-10-03、critic。goal `quoridor-4lc` / 子 `quoridor-4lc.155`、契約1・親枠10、契約Git `cfc38d0a8b6f6f3b28a5f2f8024229cc1a16fe2a`。02:12:49UTC受領、153 closed・goal継続・本人割当・pauseなしをready/showで確認し、02:15:45UTCに155のみclaim。新NN、Chrome、model-load、build、game、GPU、学習、取得、委譲は0。

**支持：固定16局の合法性・保存結果・分類・初根数値の有限成立。** 153の5入力同K機構支持と合わせ、忠実基準・教師候補・探索的対局基盤としての限定受入れを支持する。**不支持：この16局からSigma同等／正式NI、最高棋力、教師ラベルの普遍的正しさを認定する主張。** 7勝9敗は低精度の探索的結果であり、一般的な弱さも確定しない。**欠測：実store時刻、期間中の時計drift、残処理kernelCPU、実効cycle、瞬間RSS peak、全host、全deep NN一致。** 正式な実効予算公平性は不成立の断定ではなく保留。

科学停止 `c86081a4b96cca63934b0e62aa1c82ff86560ca6beeb2fd62635983074ebb304`、保存results `dd7ffd8fc10de57031696b8324cf0eaad3f553d7428beed77e3d7e39f3ccbc3e` を実byteで確認した。4登録job、8prefix、16予定game、入力SHA `20d9c9ae7284e18e4e0e30de81a2006fd65d3a0dd0e627d2ea056d5f935a5f95`、seed表SHA `ba2d4744eb5c49def80455d66c75fbe76379437f680a365a28717561ab423b25`、master74021・各8attempt seedを独自SHA算術で照合。search seed1979を全局で確認。後着151 data/report Git `0e13191bacbba7f1f92f66d3c664e2745aff26fc`、handoff SHA `def0c4b343dd0068eec9090c651ae3d70f5dc1e6b8e11b895e20e196cd1170b5`、最終stop `c6868015bac31ea2e975ed384675bc0ad8b16a39b0c9aae566c5cef0ff0b297e` は同じ科学resultsへの最小追記であり、測定版の置換ではない。旧速報8勝8敗は誤記として残り、独立に計算した保存7勝0分9敗へ原rawを変更していない。

独自 `replay.cjs` がNode VMで共有RuleAのStateのみを使い、ownerの検査器・okay・pass・verdictを呼ばず全16journalを再生した。prefix全履歴・side・壁の合法配置と残数・第三反復を含む履歴key・857公開採用手・終局goal優先／200ply draw規則・winner・final key／totalplyが一致した。全16は通常goal終局、typed fault0、未開始0、infraunknown0。共有RuleAに共通する合法性バグまでは独立排除していない。

予定16／pair8を固定して独自再算したXiは `[.5,.5,.5,.5,.5,.5,0,.5]`、平均 `.4375`。運用識別区間と双方正常terminal品質区間はともに `[.4375,.4375]`。層4／5／12／13の平均は `.5/.5/.25/.5`、各2pair。7pairは同じ盤面側が両色で勝ち、pair7だけ候補が両色で敗れた。16独立位置として数えない。参考両側Hoeffding幅は `sqrt(log(40)/(2*8))=.4801614…`、切詰め区間 `[0,.9176614…]`。これは8pair独立・boundedを追加仮定した参考であり、その独立性・被覆・代表性・.05精度は確認していない。旧149の64slotや局所敗北と合算・勝敗選別をしていない。

双方初根16（8同一state pair）はkey・履歴・side・全648特徴bits・合法209 Action順を再生状態から照合した。各根NN136logits＋valueは有限・厳密f32表現・value範囲内で、同一state双方の137値は数値および全bit一致。NN137は2,192値、特徴は10,368要素。新goldenを生成していない。4job各21実served routeは現物／生成adapterから全SHA-sizeを再構成して一致し、同Wasm SHA `500181795b373f69f6f2214ee1a77e12767e2f342e15a56ab5e27d0a0453f2c2`、同モデル `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d`、2session、Wasm ORT threads1/proxy falseを保存と照合した。launch記録Gitはnullであり、必要sourcehash／実served生成byteによる有限bindingで補う範囲を明記する。現在のmain/cacheはStageB用で、旧StageA b62cde0の測定sourceと混同しない。全build期間の依存read audit・独立browser fetchdigestは欠測。

全857公開bodyのrequest/generation・採用CP sequence／209 Action・serialized body・合法性が一致。最後のvalidated CPについてrootN、rootN−1のedge訪問和、root-inclusive backup、参照raw simulations=rootN−1／候補raw=rootN、訪問最大の合法順first finishを独自検算した。全公開inputから500ms期限、402ms cutoff、411ms予定採用を固定して確認。公開elapsedは候補410.319824–417.219971ms、参照410.275146–419.234863msで、全件500ms内。midpoint変換のaccepted cache validation終了も全件402ms未満、最小余裕は候補.030029ms／参照.100098ms。

8時計read bracketから保存lo/hiを独自再算した。CP publish wrapperの終了をmain時計区間へ変換すると、候補group1 request81 CP9は `cutoff−.130029`～`cutoff＋.089746ms`、参照group3 request87 CP42は `cutoff−.200098`～`cutoff＋.009912ms`。区間上端が跨ぐ例が各1件、区間全体がcutoff後の例は0。実adapterはmidpoint変換cache検証のreceived／validation終了を402msで拒否し、その後のSAB publishはACTIVE／generation／revisionを確認する。publish wrapper終了はexactAtomicstore時刻ではない。原規則を変更せず、cache accepted・時計区間・実storeを別証拠として扱う。区間跨ぎのみで違反／科学negativeへ変換せず、完全なdeadline保証にも変換しない。

| 保存分母 | 候補 | 固定参照 |
| --- | ---: | ---: |
| 公開要求 | 428 | 429 |
| API開始／返却 | 3886 / 3886 | 4543 / 4543 |
| 採用NN | 3533 | 4189 |
| 採用root-inclusive backup | 4181 | 5060 |
| 採用terminal-noNN | 648 | 871 |
| 返却discard／公開後返却 | 222 | 240 |

startupは4job×6＝24、sessionは各job2で上表に混ぜない。APIイベントのrequest/generation・start/run/return順・control started/returned数も照合した。公開後新NN開始の区間下端が公開後となる件数0、cutoff後新開始の確実件数0、参照のみ区間上端でcutoff後の可能性1。旧ACKが500ms後になる要求は候補1／参照3、ACK elapsed最大512.864990／547.275146msであり、それを採用遅延・有効思考超過に付替えない。相手t0が旧ACK前になる件数は候補の新要求302／参照293、自己次回収wait合計2.020264／.645020ms。双方とも保存self nextが旧自ACK回収後であることを確認した。非同期相手開始は研究adapter仕様。異なる後続局面のNN比、APIawait、ACK待ちを推論CPU・因果・同CPUへ変換せず、旧NN tail競合の実効予算への影響を未測として残す。

4job各Model drop2/activeNN0/handles0、各検索stop live search0、main timer0/message空、monitor callback timer/busy false/waited、pause reader READY/failure null/pending空／全read callback wait、探索Worker2強制terminate、inner forced/waited/登録ACK/remaining0、outer sole-root ownedwait/remaining空/unknown空を別に照合した。1213個の保存tracked identityは同bootで今回現在不在。これは自然終了・全期間・全hostの保証ではない。StageA r2のBEADS_SCHEMA_ERROR／最終JSON例外は原保存に残る。StageB group1はREADYのmonitor-stopがある一方、後続control-statusファイルはない。group2–4では私有file-backed reader／latefailure伝播後のcontrol-status READYを確認した。科学完了、exit0、primary nullだけで全監視成功とせず、未観測fault経路の成功は認定しない。必要StageB archive60memberをstreamでSHA-size／現物照合し、全copy／全展開は0。

自己checkerのr1–r6は時計符号、ACKの前後、履歴並び順、publish時刻をexactstoreとする仮定の例外。版・log・runを保持し、原NN不一致や棋力lossに数えない。修正r7で全予定局が通り、audit／binding／clock各r1で必要数値・版・停止を照合した。成功行の入力補充・原結果置換は0。自processは全wait済、source/process停止後にGitと復元hashを保存する。管理checker子の累計・sampled RSSはprocess記録を参照し、Beads／通信／Git管理費および全team費は別に扱う。新scope6MiB以内、旧保持を減額せずcritic112MiB guard以内を確認した。

最大1次案：NNUE／探索の採否に使う**学習教師データと分離した評価分布を一つ事前固定する**。本8pairの7pair同盤面側勝ちという結果から、同形式8pairの反復では小改修の差が隠れる可能性が強い。実対局由来の深さ・残壁・距離差層を結果前に定め、固定終了の色交換pairを使って改善候補の対照との差を評価する設計へ配分する案である。均衡局面の結果後選別や全保証gateを要求せず、この提案から新実行を開始しない。忠実基準のvalue／訪問／終局結果は教師候補として使えるが、教師のバイアスとNNUEへの汎化・棋力は別検証。今回156の静的準備やNNUE予備調査を待たせない。

後着最終handoff Git `f8444bdd614b031b189ce8bb11e74bce740d965e` は保存完了を記録する。final stopの1482identity現在不在は科学後pack/Git/backup helperも含む分母であり、今回4対局jobのtracked 1213identityと区別する。先行science stop、final stopのmetadata pending snapshot、後続handoff完了を同時点にしない。科学後のterminal再訪人工fixture追記は事前preflight／実対局terminal深部確認へ格上げしない。原archive7/347member全体の再監査は今回の入口にしていない。

復元・再現入口は `tools/ai-sigma-sigma-web-port-games-independent/`、必要入力hashとarchive参照は `research-data/ai-sigma/155-sigma-web-port-games-independent/input-references.json`、独自結果は `replay-result.json`、`audit-result.json`、`clock-detail-result.json`、`served-binding-result.json`。受入れはcoordinator、goal／他者close0。
