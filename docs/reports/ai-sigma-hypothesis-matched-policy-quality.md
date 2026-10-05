# SIGMA-MATCHED-POLICY-QUALITY-CHOICE / quoridor-4lc.145

**次案はC1.5／C1.0だけを変える、新baseline込みの固定Sigma相手matched12局を選ぶ。現C1.5は維持し、今回のNN・対局・buildは0。** 目的は係数の一般的優劣を証明することではなく、小比較の結果でC1枝を優先するか終了するかを決めることである。参照分布への接近や最大短期得点を品質基準にしない。

契約1・枠9、受領20:02:23.258867UTC、ready/show goal+self・pauseなし本人割当後145のみclaim。早側処理20:22:23.258867／新command20:19:23.258867／提出20:32:23.258867を保持し本人開始を配送した。144最終保存・独立採用検算を開始gateにしなかった。旧期限・結果は変更0。

判別すべき不確実性は、Cの有限選択感度が、現2Worker・500msの合法完成手と後続勝敗を実際に変えるかである。110/111はCだけの介入でjump Action31→131、asymはAction67同でも訪問分布差を支持した。旧C1 W0L4はgoal負け3＋初回eligible CP無し1、旧時計/Worker条件なので現在のC1悪化証明に使わない。119/122は固定8prefix W4L12を支持し、4prefixで両色敗北・4prefix同側winner。入力集合の粗い弱さは検出したが、小改修への感度は未校正である。旧成績と新計画は統合しない。

143の有限label支持と144早期全6certifiedwinは、非自明なラベルでもroot1／通常を区別しなかったため、同形式oracle拡張を終了する根拠に使う。静的読取中に144最終handoffが現物へ到着し、source1d96dd5/data-report47878ffを参照したが、Action/priorの最終独立採点を自分で先取りしていない。completed130は手NN26＋terminal-noNN104、startup6別。全passを深部能力や一般棋力へ変換しない。140 trueMeanFPUのinput3→133による事前quality0終了、input4の118未評価を保持する。単一C・FPU・費用に119敗因を帰属させない。

静的実根拠として、現baseline final.wasmのSHAは110 baselineと同じ `1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01`、保存C1は `8438310cf8f7d096bd84364a03b97f99f737ca0a9be6c2812a7ecdee3d92d9dd` と一致した。110 source0f0597eの一行PUCT_C diff/build記録へbindできるので、既binaryのreadonly再利用を優先すれば新buildを省ける。単なる同source名やWasmサイズで同定していない。現crates/quoridor-ai/src/lib.rs:9のC1.5、:523のQ0、sqrt(node.visits+1)、f32/seed-tie式も限定読取した。共有kernel編集0、新compile0。将来reuse binding不成立なら科学開始せず、統括が別許可した自域C-only build/parityへ判断を戻す。

別の具体的不足も見つかった。既player-main.jsのlimitsとgame記録はseed1979を埋め込み、diagnoseにも1979 gateがある。configだけ2098にしても新seed対照は成立しない。自域adapterが両engineの実context/limitsとgame receiptへ2098を配送し、NN0 mockと保存要求の実seed一致を確認する必要がある。これはA/B双方に同じ実装を適用する運用変更で、C以外の政策因子をA/B差へ混ぜない。原prefix-documentの旧search_seed1979や原結果を書き換えず、prefixの生成履歴と新探索seedを分ける。

最大1案の詳細は[proposal.json](../../research-data/ai-sigma/145-matched-policy-quality-choice/proposal.json)。122が既に挙げたprefix1/7（浅深の両色敗北）と8（同側winner）を固定し、既SHA c8104df0…286e27の合法prefix/history/featuresをそのまま参照する。事後選定の診断入力で、IID・代表性・正式holdoutではない。新生成・都合のよい入力補充・結果後の局数増量0。固定Sigma、モデルSHA d790dac6…3908d、Q0・N・order・finish・f32・capsを共通に保ち、候補WasmをA=C1.5/B=C1.0へ切り替えるだけを政策差とする。

| matched cell | prefix／既ply | 候補色 | 2局の事前順 |
| --- | --- | --- | --- |
| 1 | 1／4 | 1 | A→B |
| 2 | 1／4 | 2 | B→A |
| 3 | 7／16 | 1 | B→A |
| 4 | 7／16 | 2 | A→B |
| 5 | 8／17 | 1 | A→B |
| 6 | 8／17 | 2 | B→A |

6job各2局、同input・候補色・新seed2098でmatched、AB/BAは3ずつ。毎局fresh専用2Worker/model sessionを同じ登録warm条件で作り、前局所有停止後だけ次を準備する。live model session最大2、全24session作成、各局golden startup3×2engineならstartup72NNを手NNと別課金する。同seedは同PRNG分岐や同trajectoryの保証ではない。12局を6color-pairや12独立Xiと呼ばず、matched cell6／prefix quality unit3を別に集計する。

品質は候補W=1/true RuleA draw=.5/L=0、各variantの色2局平均Xi、prefix別差Δi=Xi_B−Xi_Aとcell差を全保存する。全3Δ非負・少なくとも2prefix改善・全cell正常完了なら、C1を次の未使用入力の限定確認へ優先する。直ちに政策採用はしない。逆方向ならこの設定のC1枝終了、正負混在なら一律C1変更枝を終了する。全得点不変ならこの集合の反復終了とし、Action差があれば尺度感度か純効果が不明、Action同ならこの条件で採用手へ介入が届かなかった可能性を保持する。どちらも「効果なし」の証明にしない。1prefixだけの変化は狭い効果に留め、この集合を自動拡大しない。自己標準算術はcell差5値の全15625人工組合せと逆方向・全不変・混在・未完了/失敗の出口を確認した。人工検査は棋力実績ではない。

全12予定slot、実開始、全fault、未開始を分母に残し、scientific retry/replacement0。候補NN/model/初回CP faultは運用loss0と合法終局品質nullを分け、係数品質の採否を保留する。参照同faultはmatched delta不成立、共通Judge/時計/identity/unknownは未完了・未採点で、0補完しない。原相手側勝敗や正常なcounterpartも保存する。ownership/guard/pause/期限なら残予定を止める。必要NN0 routing/seed/typed-fault/admission mock、実対局の初回同input root特徴・prior/finite/strict確認、独立保存12棋譜の合法・全結果・variant/色/seed集計を最小検証とし、追加NN窓・全史replay・正式NI完備を診断入口へ足さない。

思考は既nominal500ms／NN開始cutoff402／採用seal411を両variant/参照で維持する。候補limits4096/512nodes/24depth、参照100000、global RuleA draw depth200。samewallとsameK、NN回数、CPU仕事量を区別する。旧返却discard、自待ち、相手t0/旧ACK、実CPU競合・途中時計driftは保存値の限界を明記し、次相手へ残処理費を黙って課金しない。同wallの診断WDLであり、正式公平CPU/NIは未立証のまま。

費用算術は `4×[(200−4)+(200−16)+(200−17)] = 2252` 新公開ply、nominal思考1126秒。6job各250秒・browser総1500秒ならstartup/自待ち/encoding/回収等の残枠は374秒だけで、完遂保証ではない。prefix長17と対局中の新公開数を混同しない。writer35分／既binary reuse build0（必要なら別配分build120秒以内）／browser25分／独立保存15分で75〜77分の将来見積り。残親枠へ実際に入場できるか、CPU[2]単logical・RAM6GiB guard5.5GiB・保存配分は統括が判断する。提案から新jobを起動していない。

安いfixedK分布比較は既に有限感度を支持していて品質出口を増やしにくい。固定Sigmaの一手分岐続行は134で方向混在、後続policy biasが残る。wallless label追加は144で強いroot1差も検出しなかった。このため今回は、それらの反復やFPU再試行より、新baselineを含むC matched全対局を一度選ぶ。これでも固定3prefix・単seedの飽和や局面依存は残り、C改善を予測したという結論ではない。

自域静的run-r1はexit0、20ms観測runner+child currentRSS最大32,260,096B、CPU[0]単logical、wall .043979秒。原raw root追加読取0、必要summary/source/登録だけ参照、全archive展開0。旧保守8,908,800Bを維持し、142/145の直前保持1,773,568B＋既Git保守350,000B＋145新forecast1MiBでcombined12,080,944B<14MiB、追加予約0。全host12GiB再監査ではない。短命瞬間peak/初期管理command全CPU/RSS・厳密総wallは未確認、科学入力/source前後必要hash・self child wait/currentidentityと最終保持はhandoffへ保存する。default indexを使わず自域private indexでローカルGit固定、原成果・共有sourceはreadonly。

根拠は[static-results.json](../../research-data/ai-sigma/145-matched-policy-quality-choice/static-results.json)、[run-record.json](../../research-data/ai-sigma/145-matched-policy-quality-choice/run-record.json)、[storage-intake.json](../../research-data/ai-sigma/145-matched-policy-quality-choice/storage-intake.json)。再現は新許可がある場合に `timeout 60s taskset -c 0 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 tools/ai-sigma-matched-policy-quality-choice/run.py`、旧intake期限/run記録は上書きしない。受入れcoordinator、政策採用/actualgo/正式NI/Sigma/goal他者close0。
