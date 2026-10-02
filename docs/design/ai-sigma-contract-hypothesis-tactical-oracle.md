# SIGMA-TACTICAL-ORACLE / quoridor-4lc.127 / 契約1・枠8

既hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418へ単独writer依頼。121 P2を部分採用し、時間内に戦術の正解を有限に認証できるかを実装で判別する。126停止速報で同入力同時間の採用量の優劣が混在しており、単一費用原因と自動C/FPU変更は保留する。126最終版の結果は書き換えない。本文/common/現hypothesis/枠8/規約を継承、ready/show goal+self・本人割当/pauseなしを確認して本人claimと受領開始を報告。

## 問い・判断の出口
500ms比較の量差だけで改善方向が定まらないとき、合法列挙で即勝ち又は次手強制負けを避ける手を特定する狭い尺度が、後続AI評価の正解ラベルとして使えるか。今回NN0で実際に生成・認証する。正式棋力/均衡/IID/代表性は主張しない。正解ラベルが得られれば次の許可された配分で現candidate/固定Sigma/意図的stressの同入力比較を提案する。認証不能/全同じ自明問題なら拡大反復を自動採用せず、尺度枝の終了又は幾何規則・列挙上限の不足を具体的に返す。今回AIの12根評価/root1 stressを実行する許可は含めない。新NNは次配分/残枠判断と分ける。

## 最大4入力のAIなし生成と認証
121 proposals.json P2を起点とし、ブラウザ内RuleAで初期盤面から合法履歴を作る。入力は幾何規則（goal近傍/相手の次手goal脅威/双方近傍/壁による防御候補など）で最大4caseとして、生成アルゴリズム・目標・順序・上限を列挙結果を見る前に固定する。近goal到達をAIに選ばせず、モデル/value/探索/旧勝敗で入力選別しない。合法履歴から得た状態だけを使い、手番/壁残数/identityの任意改変や合法でない配置をしない。各case生成attempt上限8、適合しない場合は未生成で終え、列挙結果を見て都合のよい入力へ補充しない。全生成attempt/棄却/採用history/盤面/keyを保存。原目標に合う状態が作れないなら不足を結果にする。

生成後、rootの合法Action全列挙と合法適用、即goal判定を行い、即勝ちが無い状態では各root手後の相手合法手/即goalを深さ2まで調べる。goal優先・手番と次手合法性を守り、各case最大20000列挙node（数え方とroot込みを事前固定）で止める。上限到達・例外・合法集合不明は未解決、残branchを安全手と仮定しない。root即勝ち集合、相手即勝ち可能集合、次手即負け回避集合とその完備/不完備を別に返す。非終端の長期勝敗をdepth2で認証しない。失着はこの限定ラベル上の定義とし、200手draw/深い戦略は未判定。

独立checkerは実探索の評価関数を使わず、RuleA合法列挙だけで実行する。ただしRuleA共通実装の独立性限界を明記。簡単な即goal/脅威の小mockと上限停止/未解決を確認する。Nodeは起動/外監視/終了後保存のみ、生成・合法性・認証はbrowser内。専用AI2Worker/SABを変更せず、本NN0 checkerはモデル/探索Workerを起動しない。Atomics/時計/旧全数値の再gateを追加しない。

## 所有と期限内デバッグ
write tools/ai-sigma-tactical-oracle/、.artifacts/ai-sigma/resume-20261002/TACTICAL-ORACLE/、research-data/ai-sigma/127-tactical-oracle/、docs/reports/ai-sigma-hypothesis-tactical-oracle.md の自己域のみ。RuleA/既launcher/共有モデルはreadonly参照、必要な薄い起動adapterだけ自己域。原126/123/125/119/source結果/common/roles/registry/92/defaultindex書込0。NN/model-load/game/build/取得/GPU/学習/製品統合0。ordinary self debugは同総予算内に可、旧失敗/版/未解決を残し全copy/新issue反復なし。

静的CPU0/RAM1guard896MiB、各30秒/累計120秒。Chrome NN0もCPU[2]単logical/RAM6guard5.5GiBに課金、各60秒/累計heavy90秒。126/125 physicalChrome停止・現在identity/外heavy/headroomと予算を起動前確認し、readerror/未知ownerならlaunch0。他LLM active数で拒否0。自己保存16MiB guard14は既hypothesis予約内、旧保持未確認量を減額せずcombinedforecast確認、親保存12GiB追加予約0。

処理は受領15分又は14:08UTC、新run受領10分又は14:02、提出受領20分又は14:12の早い方。親14:05:49新重job/14:10:49監督/14:13:49monitor/14:15:49終了を変更しない。余裕不足は実施分/未実施/不足を明記して止める。枠終了後の自動継続0。

生成/認証開始とラベルの有限成立・未解決を報告し、source/Chrome/timer/monitor/innercontrolled/outerownedwait/remainingunknown・currentidentityと自然終了を分けた停止を本文前固定する。必要source/config/入力/全失敗/生成/認証根拠/停止を研究Git保存し必要archive復元確認、短報告/Beads backup→coordinator。既監督に追える判断と費用・次の実施可否を記す。goal/他者close/actual_go/NI/Sigma認定0。
