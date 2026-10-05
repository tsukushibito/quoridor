# frame22 / quoridor-4lc.280 — D保持残差の幅制約

固定primary200で距離Dを超える転移利益は支持されなかった。λ1は旧Bの後半退行を大きく抑えたが、新selectionの補正方向はまだ不利である。新selectionは既に選定に使用した12familyであり、独立test・棋力・重み採用の証拠にはしない。方式全体の反証とも扱わない。

## 一因子と結果前束縛

`teacher-rootmean MSE + 1 * MSE(v - D_initial)` をgameequal samplingの同minibatch meanで還元した。Dはlabel-free raw STM-f32距離から `tanh(8*(d_opponent-d_self))`。v3/H32/routezero4、旧train-only尺度、head0初期、Adam LR1e-4/WD0、seed19080311、batch128、2000step/256000seenは旧274 Bと共通。重みL2や推論時縮小ではない。λ1の目的は算術的に `2*(v-(y+D)/2)^2+(y-D)^2/2` と等しく、Dへ戻すだけでも損失が下がるため、罰則減少を予測情報の獲得と解釈しない。

trainは旧4653+新1328=5981行/132family。旧val1248/24と新selection392/12を分けた。初期tensor SHA `ec4167ccb5042cfe937b23850a1b52d1cd9cf6c3fb1d348627bfe6cc7d023cc5`、batch順SHA `d897f148ac328a487dd9088aa3261c21a55fac406e5a67bde121aff3216da665`、dataset SHA `f47d3032e87f17965b885134a72e4d08cb5cacb71710a362e829af9038f9ecb7` が旧Bと一致した。primary200は結果前固定。10点の曲線とLAST2000はsecondaryであり、BESTへ採否を交換しない。登録は [preregister-v3.json](../../research-data/ai-sigma/frame22-residual-penalty/preregister-v3.json)。元v1/v2・源archive・管理失敗は保持した。

## 保存結果

以下はteacher-rootmeanのgameequal MSE。旧B/Dは保存予測・曲線を再利用し、再fit/再forwardしていない。

| 評価群 | D初期 | 旧B200 | λ1 primary200 | 旧B2000 | λ1 LAST2000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 旧val1248/24 | .489404 | .479679 | .480183 | .679028 | .485816 |
| 新selection392/12 | .392634 | .399173 | .397369 | .921886 | .553384 |

primary200の新selection差はD比 **+.004734733**（6改善/6悪化）、旧B比 **−.001804500**（8改善/4悪化）。λ1で補正幅は小さくなったが、固定primaryでDと旧B双方を上回る条件は満たさない。LASTの旧B比改善は後半の退行抑制を限定支持する。新selection primaryの真z MSEは .634169（D .630042、旧B .635439）、row符号率は .785714（D .724490、旧B .750000）。符号率だけを主metricへ交換しない。zは1gameの結果であり、初期期待値の真値ではない。

| λ1 / step | train teacher | train penalty | oldval teacher | oldval penalty |
| --- | ---: | ---: | ---: | ---: |
| 200 | .382613 | .003271 | .480183 | .003204 |
| 2000 | .121677 | .096870 | .485816 | .069555 |

補正r=v−Dについて、gameequal `ΔMSE=E[r²]+2E[r(D−y)]` を保存した。primary新selectionはdisplacement .003043142、alignment +.001691591、r RMS .055164683。幅縮小後も方向は不利。LASTでは .075308878 + .085441311 = .160750189、RMS .274424631。全群・row/game・phase・rootmean/z/sign/saturationは圧縮予測とresultに保持した。少数群の平均だけで原因を断定しない。

newselectionのphase massはmiddle .872026/opening .090379/late .037595、lateは2game。middle総signed寄与には露出分布が入り、phase固有の欠陥や序盤教師安定性の低優先を証明しない。新36train追加にはtau1全plyと旧16ply以降argmaxの分布差、同seenでepochが変わる交絡がある。history文字列形式の互換は **UNVERIFIED**。state/実STM-f32入力のOR露出maskを固定したが、historyキー非一致を完全履歴非露出保証にしていない。旧開封test/173は不使用。

## 実行・検証・失敗の区別

科学は1jobのみ、13:57:12.312493–13:57:18.172780 UTC、exit0、5.863634s、CPU1単logical/Torch1/GPU0、peak family RSS 941821952B。全子wait、current exact identityなし。学習/予定評価328290、parity144、selection784で **実model NN329218**。小loss fixtureの保守32 equivalentを加え **329250上界**、managerの予約guard330074とは別記した。MAX2中1jobを使用し、追加科学予定はない。native root/Action probeはNOT_RUN、対局・教師生成・新testは0。

λ0旧criterion対応、λ1非負加算・gradient、teacher/D分離、P2/STM/f32、初期head0 penalty0を有限fixtureで確認した。初期全train/val D parityは予定step0 forward内。24固定witness（旧12/新12、両side）でprimary/LASTのfull/delta/親復帰を確認し、Torch/native maxabsはprimary 7.45e-9、LAST 5.96e-8（結果前abs1e-6+rtol1e-6）。native形式・出力式を変えていない。自己検証であり別owner独立裁定とは分ける。

runtime安全停止中のidentity=Noneを旧管理関数が参照しTypeErrorとなったattemptは **science0/job0**。v1失敗源を保持し、prospective None処理とfakeを追加した。AppServer報告の旧role definition拒否は通信管理失敗として保存し、科学不支持へ付け替えていない。科学後のcompact B-summaryの`validation`読取KeyErrorは保存算術の管理失敗で、既full curves参照へ修復し新NN0。成功科学や旧274の源・結果は置換していない。

## 重要選定と次の最大1案

最新common/hypothesis本文（281.1）を現turnへ適用した。現在方法が動いたことと、強いNNUEへ進む優先度を分ける。

| 順位・候補 | 情報価値と目標への接線 | 総費・保留理由と変更条件 |
| --- | --- | --- |
| 次1: phaseを均衡させた固定root K64/K256感度 | 学習すべきD残差方向が探索量変更で安定するかを先に問い、target取得品質と表現投資の順位を変える。rootmeanをminimax leafへ使う意味は別の未解決点 | 完全prefix抽出・資格・両K・保存を含め準備15–30分/科学30–180秒は未測見積。36root×4repeat×(65+257)=46368NNはAPI確認後の候補計画で、hidden warm/terminal/実capを別束縛。新実行は未配分 |
| 次位: 位置付きgoal距離場/壁効果の一群 | QF1+2距離では利用しにくい非局所情報を与える。DAG4一条件の負例は経路情報全体の否定ではない | P2/STM・wall更新・full/delta/undo・train-onlyscale・学習・同時間葉費まで必要。現277 map66.73%はadvance内部割合で新feature費/whole探索倍率へ外挿不可。教師残差が安定し学習alignmentだけが悪いなら順位を上げる。279同仕事全費改善は計算土台として別に評価 |
| 有力保留: independent family/分布と学習量 | 代表性・epoch・繰返しを分けて転移を測る | 新36family/12selectionは量十分の証拠ではない。同teacher量を増すだけでは不安定targetを複製し得る。入れ子のfamilyとseen/epochを記録し、候補をfreezeして未選定familyを確保。安定したteacher残差と候補利益が得られれば確認評価を優先 |
| 現対照: 出力残差幅制約 | λ1はlate退行抑制を示したがprimary新selection D超え未達 | 追加λ/LR sweepを自動先行しない。教師/入力の有用方向が確かで幅だけが不適切なら再検討。Dへ縮めるだけの成功を認定しない |

重要なAPI訂正: `sigma_mcts.rs::Search::with_limits` 第2引数は **generationで、seedではない**。`runtime.rs::benchmark` repeat0..3も同固定rootの独立乱数教師ではない。以前の提案でこれをsteadyseedと呼んだのは取り違えだった。現root探索にはroot RNG/noiseがなく、tau乱数はsnapshot後のAction抽選に使う。訂正は [teacher-source-review-v2.json](../../research-data/ai-sigma/frame22-residual-penalty/teacher-source-review-v2.json) にsource SHA付きで保存し配送済み。次案は決定的な **探索量感度** へ修正した。同root repeatは再現性/費の観測であり、独立seed分母にしない。高Kもteacher真値/minimax認証ではない。

次案はopening/middle/late各12root、train/selection各側6、可能なら一root/独立familyをlabel/loss前に機械固定する。旧late2gameから独立12lateを作ったことにはせず、必要prefix不足はNOT_AVAILABLE。保存TeacherRow.prefixの完全RuleA文脈から、rootmean/D残差方向/Action/terminal訪問とK変更を対応させる。K変更で残差方向が大きく変わればteacher/leaf用途へ、安定して現NN補正だけが不利なら位置付き入力一群へ順位を変える。現在新K・feature・学習・arenaは開始していない。

本来必要な観測量は12selectionから確定できない。未選定familyに対するpaired差の標準偏差σと目的区間幅hから概算G≈(1.96σ/h)²を計画材料にするが、σ/真効果/代表性はUNKNOWN、小標本・非IID・多条件選定の保守性が要る。教師の確率的不確実性には妥当な独立teacher定義が別途必要で、新noiseを勝手に加えない。leaf効用には完全history/terminal/同完成horizon/全合法root判断、最終利益には凍結候補/Dの同時間・色交換・多様opening・全失敗分母の強度評価が必要。今回の200step/12groupが予算内だから十分とはしない。

## 保存と引渡し

[summary-v1.json](../../research-data/ai-sigma/frame22-residual-penalty/summary-v1.json)、[saved-comparison-v1.json](../../research-data/ai-sigma/frame22-residual-penalty/saved-comparison-v1.json)、原preregister/source archiveと失敗log、全10曲線、initial/primary/BEST/LAST/checkpoints、native layout、row scalar予測を保全する。新checkpoint分類先は `.worktree/assets/checkpoints/frame22-residual-penalty-r1`。lossless archive/member SHA/lenとメモリ復元証拠、final formatter/check/lint/AST、停止identity・actualstorageは自域final receiptを正本とする。

Git/index/commitは統括だけが操作する。本人は変更path/SHA/源停止と必要byteの復元根拠を渡し、保存科学を未commit版で特定する。旧274 retain24MiB+新2808MiBの元32MiB内で計上し、旧unknown/WT/build予約を減額しない。外部reader全host停止の保証やasset削除許可は主張しない。Beads本人notes/close/backup後、goalの最高棋力未達を維持して有限引渡しする。
