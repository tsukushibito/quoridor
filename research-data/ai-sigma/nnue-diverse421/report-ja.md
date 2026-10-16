# 多様化混合NNUE421：有限結果

固定Dによる64件は全GOAL、2822 eligible rows、51T/13Vだった。名目D6はLMR ON/depth_rankのselective searchであり、full-width D6の証明ではない。規定のgame/stock抽出T-viewは927行、高壁16..20は21行、V606行中の同層は15行だった。入力family・履歴・outcome z/STM・near-goal raw±2と既存eligibilityを保持した。

公開のみCと混合Mは各29更新を完了した。Cの選択BESTはstep0/BEST43 alias、MのBESTはLAST29。C原operationのINITIAL/BEST出力宣言不足によるFAILEDは、保存fitの完了受入れと分けて保持した。Mの追加draw3712回は923行4回＋4行5回。C/M実forwards計3,874,723、M共有INITIALの追加forwardは0。

| 保存指標                 |      INITIAL |     M BEST29 |
| ------------------------ | -----------: | -----------: |
| 新V canonical-family MSE | 0.2975679592 | 0.2940229613 |
| 公開fullV MSE            | 0.4238707127 | 0.4239124679 |

新Vの小さい低下と公開Vの小さい増加を分けて解釈する。公開Vを合否gateにしておらず、正式昇格や一般棋力改善は認定しない。Mは研究候補として保持し、製品/default weightsは変更しない。

変更重みの必要な対応確認後、同じ事前6親でBEST43/M/DのD4は18 unique callsが全完成し893,657 nodes。Cの6件はBEST43 aliasとして参照した。Mのaction差は1/6、PV差2/6。p3/ply16/stock5でBEST43はaction148/value+0.331933、Mはaction14/+0.274264、Dはaction14/−0.099668だった。これは各chosen-handのroot値で、同じforced候補の値・真のWDL・旧敗因の修正を示さない。raw fingerprintとtyped digestを誤記したRoot設定で原M6が未入場だった履歴を保持し、成功12を再演しなかった。

原最初32局を再用し、元の未入場96局だけを続けた。128 unique games/64 colour-pairs、127GOAL＋1draw、UNKNOWN0、計726,360,091 nodes。四つの固定250M枠内で、未使用分の融通・補充・再演は0。

| 対照     | 勝・分・敗 |    score | 保存family-pair 95%区間 |
| -------- | ---------: | -------: | ----------------------- |
| M/BEST43 |  18・0・14 |   0.5625 | [0.375, 0.71875]        |
| C/BEST43 |  14・0・18 |   0.4375 | [0.3125, 0.5625]        |
| M/D      |  21・0・11 |  0.65625 | [0.5, 0.8125]           |
| C/D      |  17・1・14 | 0.546875 | [0.421875, 0.6875]      |

全対照が同じ16開始familyを共有するため、64 independent startsではない。原book/lineage/prefix/historyで同一性を照合し、表示名の対照prefixだけで対応させていない。C/BEST43の両typed identityは96a5と同じであり、14/18を学習済み関数の劣化へ変換できない。whole-clock/色/検索経路を含む有限結果で、一般strength/Elo/因果の根拠にはしない。

次の優先提案は高壁数coverageの明示であり、この結果から追加scienceは発行しない。独立した既許可423は自身の実pilot/count-cost契約で進め、421parent closeを条件にしない。

残96のouter461.925801297999秒を一度記録し、最初32の453.37331053300295秒は再課金しない。既知selected outer subtotal1758.734245814秒は全費用ではなく、nestedを加算しない。他FAILED/source/LLM/admin/physical NN/continuous RSSの費はUNKNOWN。旧RAW/FAILED/NULL対disk/masks、342.17/323等USERPAUSE、models/weights/seals/defaults/foreign変更を保全した。

[元の全保存解析・stock/exposure/具体例](../../../.worktree/arena-generalization377/.artifacts/research-team/nnue-diverse421-analysis-v1/final-analysis-v1/report-ja.md)、[原128局回収](../../../.artifacts/research-team/integration324/nnue-diverse421-v1/resume-after-migration-v1/collection.json)、[受入れreceipt](../../../.artifacts/research-team/integration324/nnue-diverse421-v1/publication-v1/analysis-acceptance.json)、[結合receipt](receipt.json)。
