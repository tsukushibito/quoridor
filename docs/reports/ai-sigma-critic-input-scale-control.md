# frame15 入力標準化対照・独立有限裁定（critic212）

goal quoridor-4lc / quoridor-4lc.212、2026-10-04 UTC。211の保存一対照をNN0独立算術で検算した。**固定step200の再用validation上の予測利益を有限に支持する。独立test利益、尺度が唯一の原因、教師の真値性、棋力改善は不足。**

## 選定前の見解と最終判断

同一plain QF1-H32・train96/validation24・seed19080311・Adam LR1e-4・batch順を保ち、trainのみから距離を標準化する対照は、既存情報の利用と最適化座標を低費用で調べる一単位として妥当。旧210四条件の早期利益と未検算probeはそのまま保持する。局所synthetic感度とlinear slopeの差だけを原因としない。

u=(d−μ)/σ、W′d=Wd diag(σ)、b′=b+Wd μで初期関数を保存する。ただし以後のAdam更新はΔWd=ΔW′d/σ、Δb=Δb′−Σ(ΔW′d μ/σ)に対応する。中心化・標準化・optimizer座標を合わせて変えた結果で、情報・容量の追加ではない。選定前にraw座標更新とbias結合の記録を提案し、211の実停止sourceに同before/afterからの記録が反映された。追加forward/backwardは保存source/counters上0。

## 独立検算

独立checkerは標準ライブラリのみ。共有モデル・変換関数・producer判定器を実行せず、ラベル非依存metadataのSTM順距離を別f32算術へ変換し、train96/4653行の対局等重みpopulation momentsを再算した。μf32=[0.1034392193,0.0971468240]、σf32=[0.0543474481,0.0536785498]のbitsが一致。fitへvalidation/testの距離・targetを使用しない。label-free全144metadataコンテナは参照したが、旧test labels/results/raw/journal/mixedstatus/previewおよび173正式holdoutは読まない。

raw初期e5d218c9…とprivate初期51b9a8c0…のZIP rawstorageをmodel import/unpickleせず照合した。12193 parameters、ft/out・hの距離以外の列はbyte一致。距離列W′はf32乗算に完全一致、bias補償はf32丸め許容内。保存全5901行の初期forward parity receiptはmaxabs=2.235174179e−8、許容1e−6、step前にPASS。これはsource/receiptとstorageの有限bindingであり、criticによるforward再認証ではない。

新旧config・train/validation hash・400step batch SHA83eb87b8…・全6 named parametersのoptimizer所属が一致。10時点0/1/2/5/10/20/50/100/200/400を保持し、保存96train/24validationの対局別MSEから対局等重み/row重みを別に再算、z/sign/saturationのrow集計も照合した。固定12witnessのhashによる所属、旧新の表示順、rootmean target、residual、tanh/preoutput、初期差と予測変化を照合した。全prediction再生成や教師truth/historyの再証明は行っていない。

| 保存値 | 元209 raw距離 | 211 標準化 |
| --- | ---: | ---: |
| step200 validation rootmean gameMSE | 0.6598473195 | 0.6139164436 |
| step200 validation rootmean rowMSE | 0.6477449213 | 0.6044741006 |
| step200 validation z gameMSE | 0.9879228485 | 0.9456283895 |
| step200 validation z符号正解率（row） | 0.5400641026 | 0.6193910256 |
| step400 validation rootmean gameMSE | 0.7196768814 | 0.6487715053 |

結果前primary200の差は−0.04593087594886214。24局中20局改善、局別差の範囲[−0.1428248833,+0.0225415140]。同25600 train samples・5.5018相当epoch。標準化train gameMSEはstep200で0.5485668559、400で0.2572832050だがvalidationは200→400で悪化した。BEST200はsecondary記述で、primaryを結果後に選び直していない。train-only定数のvalidation gameMSE0.6787804677を超えたが、距離基準0.4851468131との差+0.1287696304を保持する。

開幕6cohort各4局とphaseを結果へ保存。開幕20ply cohortは定数より悪い。validation lateは0行/0局で未知を0誤差へ補完しない。cohort/phaseの数値は保存予測集計の照合範囲であり、真の新分布への一般化ではない。

距離列の第一更新は標準化座標norm0.0007873881、raw座標norm0.0145785930、比18.5151。σによる逆変換boundsとnorm/RMS/要素数を独立確認した。raw bias normは0.0010873197、標準化bias0.0005567813。per-step個々のdeltaは非保存なのでaggregateだけからbias結合を再構成したとは主張しない。固定witnessの初期からの予測RMS変化は200で0.2122204310、400で0.5081284116。変化の増大単独を有用情報利用とは認定しない。

## 全費・停止・限界

211 CPU2単1の科学jobは04:53:55.363652→04:53:58.461697、3.098458861秒、exit0/全wait/remaining空、peak family RSS787820544B。train51200+通常eval59010+追加raw初期parity5901=116111 samples。通常trainer110210と分け、parityを費用から除かない。observerの排他overheadは未測、job wallに含まれる。API/pipeの時間を排他CPUへ加算しない。prep/管理/記録の未測全費を埋めず、このwallを全pipeline時間へ拡張しない。

criticは直前supervisor ownedNone・次quiet>150秒・211 PID/tick不在・関連scienceプロセス不在を確認してCPU0短算術を実行した。点観測を将来/全期間/全host保証にしない。検査器のwrapper誤分類、witness表示順の仮定による2失敗版を保存し、同算術枠内で修復。成功checker約0.15秒・peak RSS54747136B、NN0。212はsource/read60+有界算術/修復60=120/120の保守的charge。旧210180/180は不変。

## 次の一判断

**距離列の実効raw更新を制御した一対照を次候補とする。** 約18.5倍の座標増幅があるため、中心化とbias補償を保持しraw距離列のstepを揃え、今回の利益がその増幅だけで説明されるかを低費用で判別する。joint seed再現も有力だが、まずこの交絡を直接制約する方が原因候補を狭める。新runを自動要求せず、既存候補/残費との配分は統括が判断する。

一joint seed、複数条件で再用されたvalidation24局、center/scale/Adamの結合介入の範囲に限る。教師/history/分布・活性/情報利用・早期過学習の競合説明は残る。既定昇格・Sigma同等/NI・新testの救済は0。独立結果とbindingsは research-data/ai-sigma/frame15-input-scale-independent/result.json、失敗版/停止/保存会計も同scopeに保持する。
