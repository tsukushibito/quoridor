# 429.3 実データviewと少数学習条件の準備完了

**source/config・実view・費用提案の完了であり、fit/eval/対局の実行許可でも結果でもない。** 元のsource受入れと今回の保存済みviewを区別し、Main/Git/Cargo/今後の実admissionは324が所有する。

## 実データと固定view

Bの元1280要求から1204完了（1190GOAL/14threefold）、76入力欠測、62186eligible行（T49911/V12275）。quantity1018game、early186gameであり、request/game/canonical family/入力distinctは同一ではない。native共同partitionのV全12275行を全条件で共有し、削除・cap・再partitionしない。cohort間の共有familyも独立標本に水増ししない。

既存の各game×stock層16..20/8..15/1..7/0からchronological最大8行を先に抽出し、T候補18822行。固定したoutcome-blindの入力代表・層quotaにより数量small3735、large14940、early-matched3735を作成した。目標3763/15052への不足28/112をrepeat/refillで埋めていない。early側の実distinct容量は3861。quotaはsmall[322,1164,1617,632]、large[1288,4656,6468,2528]で正確に4倍、smallはlargeに含まれる。eligible外/V/cap外を追加しない。

| 固定view | literal distinct | game | family | stock18..20 |
| --- | ---: | ---: | ---: | ---: |
| quantity-small | 3735 | 798 | 796 | 1 |
| quantity-large | 14940 | 813 | 811 | 5 |
| early-matched | 3735 | 149 | 149 | 818 |

earlyは同じ総distinctでもstock構成が意図的に異なる別対比である。各family/gameの重みが等しい比較とは呼ばない。元423Tは新viewへ含めず、旧source203T53V→final204T52V/ID18の対応を改変しない。旧423との直接model-input overlapと公開game/history欠測はUNKNOWN、旧cache/RAW/sealed/newEは追加で開いていない。

型付き正本codecのinjective geometry+FP32 distance keyを利用し、z・q・予測誤差で代表や順序を選んでいない。全共有Vとliteral/LR入力orbitが交差するT family除外は実0だった。base候補内literal alias15行を代表に統合した追加downsampleであり、旧row multiplicityと同じobjectiveではない。独立sample数やWDL/履歴の証明ではない。

## 将来4条件の費用提案（全て未実行）

| 条件 | T distinct | draws | updates | 最終tail | train+measurement上界 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Q-small-8exposure | 3735 | 29880 | 117 | 184 | 545838 |
| Q-large-fixed-draws | 14940 | 29880 | 117 | 184 | 563666 |
| Q-large-8exposure | 14940 | 119520 | 467 | 224 | 653306 |
| early-matched-8exposure | 3735 | 29880 | 117 | 184 | 545838 |

shortは116full×256+tail184、longは466full×256+tail224。actual Nから再計算し、旧target118/471を使っていない。large-fixedは平均2露出、他は8露出。row-indexだけの既存sampler計画で各行の予定回数と順序digestを保存した。これは実fitのexposureではない。

同じBEST43/fresh Adam、LR1e-4・最初10updateのlinear warmup後constant、z MSE、FP32/QF1/FT32H32/Zero4/tanh、incumbent T-only尺度/output bypassOFF/reflection.5を保持する。新しいoptimizer/model/teacher設計やweight昇格はない。観測点はshort0/39/78/117、long0/156/312/467。INITIAL/BEST/LAST、family-MSE/tie-earliest、public non-regression=false。公開T8192は別panel、公開openedV419150は各frozen BESTで一度の提案。全viewでT panelのsupportが同じとは主張しない。

訓練draws計209160、normal planned_workが保存した訓練+測定の提案上界は2308648 logical rows。異なるviewのINITIAL共有に仮のcreditを取っていない。changed-weights対応やstrength工程の費用は未設定で、whole fit support/Experiment/runtime/重み/実INITIAL observationも未作成。Bの未使用Sigma枠、旧4M、別研究の枠を転用しない。

固定draw/update、固定exposure（計算4倍）、同distinctのcoverageを分ける。long途中117/旧118更新をshort tailの学習済みweightに見立てず、四つの将来条件として記録する。V選択回数や各T panelの差も残り、多様性だけの因果・優越・強さを結論しない。

## 既存受入れと原失敗・summary修復

optional mixture.training_viewは独立429.4 clear0/0後、Rootが正確な5片をMainへ疎合成し、実moduleの新4metadata testを別scopeでPASSした。authorの凍結fragment4PASSを再演していない。実view FileRefsはnormal ordered Experiment.inputsとbefore/after lifetimeへ将来joinする必要がある。source受入れは科学実行の許可ではない。

今回のmaterialization-v1はsource_indexをproducer slice番号と誤同一視したauthor assertionでFAILED。input-source namespaceを保つ修正後、v2はview/config/予定exposureと検査を完了したが、summary中のNumPy int64のJSON保存でFAILED。元記録とinvalid summary.jsonを保全し、選択/config/露出の再実行0でsummary.repaired.jsonだけ別commandで保存した。修復は固定indicesの不足したstock記述を正本RECORDから読むだけで、model key/反転/label/公開payloadやforwardを追加していない。

publication erratumとして、small LRorbit=3735は元partialに既に保存されていたことをsummary-publication-erratum.jsonへ明示した。repaired summaryの当該null/未保存という説明はsmallについて広すぎる。large/early LRorbit数と、失敗時に未保存だった元source-ref完全一覧はUNKNOWNを保持し、元のbefore/after検査が成功した有限receiptと混同しない。view/config/exposure/費用の数値は変更0。

## STOPと残る境界

元view/checkerのSTOP05:19:05.574115Z、summary修復helperのSTOP05:28:10.016378Z。directwait/reap・fresh exact child absence・map/handle close・TMP/lease/owned[]を各原receiptへ保存した。430の実native+collection STOP（reader05:48:57.425864Z、collector05:51:47.395908Z）によって前のtiming holdが解除され、今回の最終scopeは保存メタデータ/report/backupのみである。新しいquiet/idlelease/将来の資源保持を主張しない。

NNUE/Sigma/model forward、fit、Search、game、bootstrap、新生成はauthor0。model/公共payload/旧RAWのコピー・全再hash、旧成功suite再演0。全旧USERPAUSE/default/models/seals/RAW/FAILED/費UNKNOWNを保全する。連続family RSS peak・全費用・global actual占有はUNKNOWN。ordinary affected usageは限定追加分だけを一度記録し、旧holding再課金・減少refund・global walkをしない。

残るのは324によるこの保存packetの通常scope受入れと、その後の本人leaf close/backupである。将来fit/eval/arenaはこの完了から自動入場しない。親429/430/324はRoot所有で、本人closeや返答を430保存分析のgateにしない。
