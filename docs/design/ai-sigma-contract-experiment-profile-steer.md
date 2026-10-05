# SIGMA-B0-PROFILE / 子issue quoridor-4lc.5 / 試行1 / 契約版2（方法補足）

既存契約 ai-sigma-contract-experiment-profile.md のscope/owner/場所/全体上限を継承。目標quoridor-4lc、docs/design/ai-sigma-research-goal.md版1のユーザー権限による統括の方法更新。予算追加なし。開始17:46:09UTCを保守基準に期限18:56:09UTC、18:18UTCで約38分残り。GPU/モデル/学習/最適化/正式対戦は開始しない。自分の子issueだけ所有、書込み範囲そのまま。

SIGMA-COMPARE-CRITICを受信し、docs/reports/ai-sigma-critic-comparison.md（SHA256 607618c36454a18bb4f9ba2ec954b074a58e82214648e7991f5030b8400c74cf）を読む。H1方法への以下の条件を採択する。統括もprofiling.rsを読んで、現在のkind×直近parent行列だけではExpand内/外のDistanceを復元できない点を確認した。

1. 主比率 R_exp は「Expand内のLegalまたはDistanceの部分木時間の和集合」/Expand inclusive。stackにExpand祖先/phaseを持たせるか、union時間へ直接charge。global Legal/Distance時間をExpand総時間で割らない。評価中Legal/Distanceは含め、Search→Transition内はExpand外として除く。重複計上なし。
2. R_all（同unionの全検索時間/T_search）とf_expandも記録。R_exp高いだけで全検索支配としない。R_exp>=.50支持、<.20不支持、間は保留。局面別の結果・cap/overheadで結論が変わる場合を保持。
3. 主時間分類のoverhead gateを各caseのmedianで5%以内に事前固定する。元3samplesは保存し、可能なら結果前に各fixture warmup1+10samplesへ固定してunprofiled/coarse/fullを順序交互で測る。5%超過ならcoarse/低頻度等へ切替、比率判定できなければ「計測不成立/判断保留」としH1のnegative resultにしない。期限内に妥当な器が完成しなければ元B0/隔離成果と失敗条件だけ報告する。
4. 同条件の決定的出力/合法順/手/visits/value等の一致、instrumentation自体の追加確保有無、real allocator未計測は未確認、exclusive和/残差を検証。親kindのinclusive行列を再帰加算して祖先unionを再構成しない。
5. 原3fixtureとP2/jump/壁多数等の追加分析入力を分ける。主規約はまだ原B0標準ルールの診断で、正式Sigma比較ではない。内部history/context/同実時間adapterが未整備なため正式対戦はno-go。

新しい調査hypothesis .6がCPU0で小さいテキスト/メモリ確認のみを並行する予定。あなたの測定窓を公式無競合と称さず、heavy準備の同時実行なし/CPU2/背景負荷とoverheadを記録。統括へ報告し次の方向を決める。pause/異常/締切で自己job停止・終了状態回収・証拠保持、書込停止、Beads backup、既存report経路 --issue quoridor-4lc。次の追加scopeを自分で拡張しない。
