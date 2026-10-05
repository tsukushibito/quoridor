# 固定Sigma-Webの忠実Rust/Wasm基準と同wall診断 / 151

固定5入力の同K32比較では、修復版のpath・合法順・訪問数・Action・true value ledgerが全CPで対応した。新8prefix×色交換の16gameは基準候補7勝0分9敗、全16予定scoreの運用・terminal品質識別区間はともに[0.4375,0.4375]。独立bounded pair追加仮定だけの95%参考区間は[0,0.9176614]で、差未確定。Sigma同等、正式NI、一般棋力、親目標達成を認定しない。親の最終目標は現在NNUE型最強AIであり、本版は初期段階の基準・教師生成/評価基盤候補である。

## 実装と参照境界

研究自域private crateの実policyはC1・sqrt(parentN)・未訪問true parent mean−.2 sqrt(visited original/basePrior和)・訪問child=-childQ・strict greater firsttie・temp0 visit→first。rootNNはtrue ledgerへ一回加算しloop外、K32はrootN32/edge31。pawn方向順の後、wall(y,x)ごとH→V。P2特徴と136policy垂直permutationは各一度、jumpの209は実着地で対応。合法history再生、第三反復手の除外、goal優先/totalply200drawを既ルールで保持した。NN f32を正確にf64へ拡張し、masked softmax/mean/PUCTはf64、tree演算の丸め救済なし。

固定Web源751186344fc52ad0c29bc65922e62c6fa915f006のMCTS遷移を移植した。研究CP/SAB/時計/cancel/strictfault/terminalrootNN0/yield/guardは運用adapterであり、原Web全運用の同一性ではない。NN例外random rollout fallbackは診断へ混ぜない。共通ONNX d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、ORT1.21 CPU/Wasm各1thread、2独立Worker/session/SAB/control/generation。通常は手番だけ、自己旧zero後開始、相手t0の旧ACK待ちを前提にせず、旧返却discard。

元candidate immutable1f54d0b8…78a01/旧149/共有kernel/model/refを書換えず、私有targetでcached offline locked build。root/depth安全guardは200000node/depth200/nominal node arena128MiB（全context heapは外RSSguardを併用）、共通運用要求上限100000。旧512/depth24を残さず、到達はrefusal/unfinished扱い。本16gameの候補最大1603node/depth11、guard到達0。参照node/depthは欠測で0へ補完しない。

最終実行binary SHA256 `500181795b373f69f6f2214ee1a77e12767e2f342e15a56ab5e27d0a0453f2c2`、282867bytes。compiler `rustc 1.98.1 (48a229cea 2026-09-01)`、Cargo `cargo 1.98.1 (797e8a9bc 2026-08-05)`、flags/lock/依存はbuild-binding-r3.json。必要7未Git library差分と9入力hashをdependency-binding.jsonに保全し、現物終了hash一致。Gitだけで未Git依存を再構成可能とはしない。原baselineと新基準の政策を同一視しない。

## 機構診断と失敗

NN前登録5入力はinitial-p1/asym-hv-p2/straight-jump-p2/旧149未開始prefix13,14のみ、historyから再生。固定入力SHA `dc205f8d7e00ee52aca51845ddbca5e3085d0aebdb22c3f4ceb6fa139cd10954`。150静的裁定はreadonly参照、実Wasm成功へ代入していない。

NN0実Wasm/原JS人工oracleではK1first finish（最大priorは後手）、equal-score tie、root count/mean/符号、depth1〜7、goal200優先、repeat手除外、P2jump/壁順を支持。20＋f32 ABIチェックを保存。人工NNと実modelを区別する。先着terminal到達はNN前に1回だったため、terminal再訪NN0の確認は停止後の同binary K16人工oracleへ追加し、9 terminal-noNN、同path反復とNN calls不増を確認した。AI前の再訪fixture完備へ遡及変更しない。

r1科学source c706326、手NN320/startup6/session2、rawSHA75a09f52…93bb4を保持。JSON ABIで元f32値0.21437489986419678がf64 1ULP違いへdecodeされ、true root ledger不一致。旧first_discrete_difference=root_ledgerのラベルは数値差であり、path/訪問/Action実差とは別。原解析を保存してerratumを付けた。f32 bit復元→f64正確拡張へ修復、新source b62cde0/r2は追加手NN320、旧行の置換なし。

r2全5pair・各32CP・160対応model要求・725実selectでstate/history/features/137NN・全backup/edge訪問・Action/pathが対応、root/child ledgerとmeanはexact。最初のprior差2.1684e-19、最大prior差1.7347e-18、最大chosen-score差1.1102e-16。選択pathに差0、全未選択score順位/全深部一致は認定しない。記録on/offは保存r2 NNを再生したNN0で160CP対応、追加実NN0。

r2の最後worker完了は01:41:23.263345UTC、monitor読取は01:41:23.011開始→01:41:28.166返却、01:41:28.167 BEADS_SCHEMA_ERROR。summaryprimarynullを監視全期間成功へ変換しない。原stdoutは未保存でparse error記録のみ、原因を確定しない。private file-backed wrapper reader/少数mock・有界1 schema retry（未知はmonitorcheckが拒否）とfinally controlfailureの別保存を修復し、次job前READYを確認。r1/r2や完成科学行を再実行/救済しない。

build-r1 admission FileNotFound→spawn0、NN0 oracle-r2の誤った人工leaf期待値、generation-r1のmock SnapshotCache参照例外、collector-r1のclock field誤読も保全。検査器/基盤例外をNNloss・棋力lossへ付替えない。

## 同wall16game

master74021/domain port151-stageB-v1、SHA domain derive→xorshift32。4/5/12/13ply各2prefix、class pawn/wall1/2→元合法順一様、最大8attemptの最初合法非終端、重複flag保持、AI/model/value/filterなし。新8すべて生成、旧149成績に統合せず、seed table・入力・16順・4×4game管理jobをmodel load前に固定。T500/cut402/adopt予定411/bounded2sample/seed1979、goal優先200draw。全16予定分母、候補fault0の運用と両fault未知のterminal品質を別集計。今回はfault/infra/unfinished/unstarted0。

| pair | ply | Xi | 同盤面側winner |
|---|---:|---:|---|
| 1 | 4 | 0.5 | 1 |
| 2 | 5 | 0.5 | 1 |
| 3 | 12 | 0.5 | 2 |
| 4 | 13 | 0.5 | 2 |
| 5 | 4 | 0.5 | 2 |
| 6 | 5 | 0.5 | 1 |
| 7 | 12 | 0.0 | 候補両色敗 |
| 8 | 13 | 0.5 | 2 |

正常terminal complete-only m=16/mean=.4375は補助。pairを8標本とする仮定のみのHoeffding eps=.4801614、独立性/被覆/均衡/代表性は未立証。7pairのXi=.5は同盤面側winnerで、各AIが一勝したことを一般同等証明へ変換しない。pair7は候補が両色で負けた。速報の8勝8敗/全Xi=.5は本文誤記で、保存raw/集計7勝9敗は不変、原速報＋訂正を保全。

全8初根のkey/history/side/合法prefix/features exact/NN logits・value exactを支持。後続は異なる状態で、総NN比を機構因果にしない。

| 保存分母 | Rust基準 | JS参照 |
|---|---:|---:|
| 通常要求 | 428 | 429 |
| API starts/returns | 3886 | 4543 |
| 採用CP completed NN合計 | 3533 | 4189 |
| 採用CP completed backup合計 | 4181 | 5060 |
| 旧返却discard | 222 | 240 |
| 最終validated CP terminal-noNN合計 | 648 | 871 |

startup24/session8は上記から別。API await平均C34.0205ms/R34.1744ms、firstCP平均C98.8902ms/R54.3638ms。firstCPはworker-main endpoint clock変換の観測で、APIawait・ACKwallをkernelCPUへ変換しない。採用completed backup median C8/R9、候補量が小さくても品質因果/同CPUを認定しない。確定後新NN startsの保存clockでdefinite0、cutoff definite0/参照possible1、旧返却after-public C222/R240。途中drift/exactAtomicstore/純NN CPU/全背景負荷は欠測。後続総量・異なる局面を同仕事にしない。main審判/時計/合法性/結果、Node起動・外監視・対局終了journal保存のみ、毎手Node CP/時計前提0。

## 停止・費用・保存

最終AIheavy終了01:59:31.444851UTC、全4group/各pairの停止速報を先送付。Modeldrop/NN/search/main timer-message/monitor callback/inner controlled/outer sole-root ownedwait remainingunknown/current exact identityを各stop正本で分離。全group current monitor READY、r2 late control failureは別保全。現在不在を自然・全期間・全host停止へ格上げしない。科学source/実runtime停止後は必要pack/解析・報告helpersのみ、実NN/build/game追加0。

管理job部分wallはbuild7.701s、StageA56.354s、StageB生成・失敗・4group込み444.930s、protocol/packはresource-and-dependency-final.json。StageA実手NN640＋startup12、StageB startup24別。追加の短いread/edit/Git/通信費は一元実測がなく0としない。配分static300/build180/A300/B1800、CPU0静的/CPU2重job単logical、ORT各1thread。browser+Node peak current RSS約1.85GB、guard5.5GiB。予算の全期間実使用や純CPU保証ではない。保存は64ではなく既151配分256MiB/guard224MiB、現在保持・未使用予約・Git forecast/過去peakは別、親追加予約0/旧未知量減額0。

archive7個/必要{sum(x['member_count'] for x in m['archives'])}member・全member SHA-size stream照合、必要member実展開＋再hash。必要source/7依存patch/lock/compiler/binary/served hash/input/全attempt/棋譜/clock/失敗/stopを保存、共有model/依存/target全copyなし。pack以後の停止helpersはpost-science-helper-records.jsonとhelper sourceで別分母。archive-manifest.jsonに原展開先/最小復元先、source Gitとdata/report Gitとhandoff metadata Gitを区別する。

## 最大1次案

同モデル/政策のroot入力準備（合法履歴再生と重複context生成）境界だけを再利用/削減する案。根拠は同K機構対応と、同wallでfirstCPがC約99ms/R約54ms、採用量Cが少ないという有限観測。API/kernelCPU原因や7/9の因果は未確定で、既保存root prepare spanは次の境界特定に使える。新実装はfresh tree・実history/third-repeat・P2/orderを保ち、NN0→固定5input K32対応→新事前固定同wallで差が残るか反証する。見積static300/build180/機構browser300・実NN最大1024、対局を選ぶなら別配分16以内・1800s/同CPU/RAM。現在枠で自動開始せず、量だけ増えて品質差が未確定なら採用を保留。忠実基準を教師/評価基盤として保持し、NNUE学習/GPUや他因子へ自動拡張しない。
