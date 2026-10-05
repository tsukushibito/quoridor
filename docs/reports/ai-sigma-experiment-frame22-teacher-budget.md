# frame22 決定的教師の探索量感度 — 282

全phaseの感度判定は未成立。資格2rootは有限PASS、主測定は記録途中で180秒上限となり、登録96条件中4条件の完全レコードだけを回収した。科学MAX2を消費し追加runは行っていない。高Kを真値、繰返しをseed分散、今回を棋力評価とは呼ばない。

## 条件・入力・分母

Sigma d790、既TensorRT engine 5be20cf0、常駐Graph B1..8・この診断の実infer batch1、同精度/探索規則。`Search::with_limits`のgeneration=1は乱数seedではない。固定rootにnoise/RNGなし。新game/teacher学習/モデル取得なし。WTはmain279採用前の停止coreを保持し、main速度成果を移植していない。

登録はラベルを見る前のmetadataのみ。ply<20/20–59/60以上、phase内family昇順、最初eligible row、一family一root。完全prefixをRuleA再生しstate/history/side/ids/STM距離/feature_signatureを元Arrow行へ照合した。history hashから履歴を推測していない。

| phase   | 登録train | 登録selection | 予定から不足 |
| ------- | --------: | ------------: | -----------: |
| opening |         6 |             6 |            0 |
| middle  |         6 |             6 |            0 |
| late    |         6 |             2 |   selection4 |

36予定root中32登録、各K64/256/1024で108予定条件中96登録/12NOT_AVAILABLE。全32登録rootはP1であり、同family跨phaseの相関もある。後からP2や別familyへ補充しない。既selectionは開封済み資料で未見testではない。

## 資格・実処理・失敗

資格はP1/P2各1root。CPU/GPU137出力finite parity最大絶対差3.34e-6/3.58e-6（固定abs1e-4+rtol1e-4）。両K64完成、Action13/75一致、πL1=0。rootmean差約+2.68e-7/−2.96e-7。全tree bitexact・教師真値の証明ではない。CPU参考130+GPU130+shape warm36=296physicalNN、allocated24914。

主job `3139297e-925b-44dd-b34c-79e3b7a2264e` はHARD_TIMEOUT/exit−15、command180.516275s、背景185.146986s、全wait/currentexact[]/cleanup成立。guardの最終assert失敗は停止結果の伝播である。GPU数値不一致・棋力敗北へ変換しない。

主出力は65727BでJSON途中切断。元bytesを保持し、完全JSON objectだけ4件を別NN0集計器で回収。92条件はUNKNOWN_NOT_RECORDEDで、全て未開始とも全て完成とも補完しない。先行headerのlogicalNN5376/allocated515334は、同期records書込み前に計算されたcounter。途中serialization中に次のinferは進まないsource順序とwarm36から、主physicalNN5412、資格込み5708をsource-boundで別記する。原guard NN UNKNOWNを書換えず、さらに保守上界98296も保持する。総allocated source-bound540248。processedは未記録、advance回数/allocatedとは区別する。

停止時の同PID最終標本はD状態・CPU ticks2176であり点観測。直接`serde_json::to_writer(File::create(...))`が各条件後に全既存recordsを再書込みし、切断位置もその書込み途中だった。記録I/Oは具体的不足候補だが、wholewall全額を排他的I/O/CPU/GPU費に帰属する計測ではない。

## 回収できた値

| root       |    K | Action |  rootmean | search秒 |
| ---------- | ---: | -----: | --------: | -------: |
| game0 ply8 |   64 |     13 | −0.210367 |  .133533 |
| game0 ply8 |  256 |      3 | −0.230061 |  .310183 |
| game0 ply8 | 1024 |      3 | −0.366652 | 1.311713 |
| game1 ply8 |  256 |     13 | −0.436365 |  .838388 |

同rootで全3Kを比較できるのはopening/train/P1の1rootのみ。K64→1024はΔrootmean=−.156284、Action13→3、edge visit正規化πL1=1.272820。D0,8=0に対する残差は全K負、符号は変わらない。K256→1024はAction3を維持して値−.136591、πL1=.344891。末尾terminal originはnull。これで高Kの正しさ/有用leaf教師/棋力利益は判定できない。中盤・終盤・selectionの感度はNOT_ESTABLISHED。

## 全費と保存

compile+clippy command35.780503s/上限120、資格+測定command195.636228s/科学300内。NN0 replay+回収分析command10.715031s。native span、guardian、背景のinclusive wallは重複するので加算しない。未測read/LLM/管理費はUNKNOWN。NN0保存用script初回lintのunused importを管理版で除去し最終format/check/lint PASS、旧実行版はarchiveに保持。科学sourceや失敗bytesを修正していない。

主peak RSS473694208B、GPU全device標本上界2651848704B/140標本。専有processVRAMはUNKNOWN。資格のdevice標本上界1736441856B。device値を専有VRAMと呼ばない。

必要source23member archiveの全member SHA復元PASS。scope current1246751B+保守uniqueGit550979B+残metadata262144B=2059874B、guard3670016/reserve4194304内。旧273123MiB+2781+2824=128MiB、旧unknown/保持は割引なし。共有release reserve128MiB内で増分を保守確認。Git/index/commitは統括のみ。

正本は `research-data/ai-sigma/frame22-teacher-budget/{science-stop.json,management-stop.json,compact.json,salvage-result.json}`、原途中出力・全process/background receipt・source archiveを参照する。scientific stopと管理lint修正後のcurrent source止束は別版。独立採否は統括、本人解析は自己検証。

## 次最大1

次の別配分では、管理recordingをBufWriter/一度のbounded atomic snapshotへ薄く修正し、NN0のschema/切断復元を確認後、今回結果前選定したphase32rootのK比較を一回完結する案を推す。これは今枠の再実行許可ではない。欠測のためteacher安定性を特徴追加/量増加より恒久的に先行する根拠はまだないが、唯一回収rootの値・Action・πはK感度を示し、教師budget仮説を未検証のまま棄却する情報にも足りない。

必要NN上界32×1347+warm36=43140（資格は別枠必要範囲）。今回1rootの純search3K合計1.755429sから32root約56秒は粗い参考外挿のみ、中盤/終盤・再生・backend初期化・記録/保存はUNKNOWN。薄修正のcompileは今回14.43秒、clippy2.73秒を参考に別command上界を計上する。完成後K差がphase横断で小さければ、位置付き経路/壁効果とrootmean→minimaxleaf/horizonの競合を次設計へ戻す。差が大きくても高K大量生成を自動採用せず同時間の独立量/教師有効性との費用比較を要する。全map情報欠落、量十分性、NNUE方式不成立、最高棋力goal達成は認定しない。

## 同課題内の明示一回修復配分（14:47以後）

統括がMAX3（旧2+最後1）、旧NN100000を保持して追加50000/総150000、旧allocated12mを保持して新8m/保守20m、旧科学300秒は維持、NN0準備+30秒/管理+30秒、保存追加2MiBを明示した。旧MAX2/rerun0報告の時点・失敗を変更しない。新science/source14:57、保存15:05の個別期限は新frame23親延長で救済しない。

BufWriter＋明示flushのみを共通JSON保存入口へ導入。finalは既所有partial pathを再利用して最終pathへrenameし、二つの全raw出力の同時保持を避ける。JSON値/順序/schema/浮動小数表現、モデル/探索/teacher/D/入力/K順/Limitsは変更しない。旧compact source・binaryもxzからSHA復元PASSで別保持。新writerと同一functionの207B有限fixtureで旧serde writer bytesとの完全一致/完全decodeを確認した（全tree数学の新検算ではない）。

最初のビルド入口は旧frame22正stateがstopped/processNULLで、child前に拒否、build0/NN0。14:53:13の新runtime-applied受領後、registry.current_operationがframe23-extensionであること、current24/hash/正scheduler1430721 tick46503900・monitor1430738 tick46503929を新私有guardでfresh照合。旧frame22stateをrunning/freeに読替えず、新bindingへ切替えた。

NN0 fixture/build/clippyはPASS、command20.264599秒/追加build25秒以内、peak274128896B、全wait/currentexact[]。全compile等は旧35.780503＋新20.264599=56.045102秒で120秒以内。新binary SHA61279695634132a59a1e713bb9b6521b1d3d1bbaee786b63d0f655935a136e60。Rustfmtと既project設定のRuff format/check/lint PASS。原source/失敗/archiveは不変更。

この後は14:57までに科学hard90秒＋回収余裕が入らないため、最後の科学は **NOT_STARTED**。新forward0/新科学0秒/最後slot未消費、同32root×3Kの96条件を全てNOT_STARTEDとして別結果へ保持した。旧92UNKNOWNを修復成功へ置換していない。現在CPU不足/GPU数値不成立を原因と確定せず、正runtime復旧後の個別時計不足を示す。science追加第四/資格再forward/Kやroot変更はない。

修復必要source11member archiveは全SHA復元PASS。旧4MiB current2000860B＋必要Git等の保守補足=2913004B<旧3.5MiB、旧forecast2059874Bの証拠は維持。新2MiB current184925B/forecast500922B内。273121＋2781＋2826=128MiB総不増、unknown減額なし。正本は `repair/{result-not-started.json,source-stop.json,build-result.json,build-r3-newbinding/process.json}`。親frame23への延長は研究管理の現bindingであり本個別runの期限/上限のリセットではない。

次最大1は、別明示配分が得られれば今回完成した出力修復版と元phase32rootのK感度を一回完結すること。未計測のteacher安定性と葉/horizon・位置情報・独立量の競合を、1rootのK差だけで固定しない。今回の到達点は有限資格・部分感度・記録修復検証・未開始保存までで、一般性能や最高goal達成ではない。
