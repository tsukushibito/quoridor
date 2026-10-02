# 131・停止129の有限戦術ラベル独立裁定

**保存12公開のラベルpassと分母を有限支持する。この4入力ではroot1と通常探索を区別できず、完成量改善や小改修の比較尺度としての感度は成立していない。** 狭い同形式反復を終了する判断は妥当。一般戦術・長期棋力・正式公平性・NI・Sigma同等・係数採用は未認定。新Chrome/NN/model-load/game/holdout/build/取得は0。130の開始条件を追加しない。

受領15:49:28.391159UTC、ready/show goal+self・pause無し・本人担当を確認して131のみclaim、開始報告accepted。処理16:04:28、新command16:01:28、提出16:14:28の早側を保持。枠9/common/critic/目標/実行規約全文を継承した。

原129測定Git `766605299347c46869a2154afe27412162917d2f`（自己実装d230ba6）、保存helper207badd、data/report9c6b41c、handoff daafb4dを区別した。handoff SHAfa9d8b0eedfa7e1c2f085c9654f5819dd61a8f7387ead9f112e6d29d2c264516、stop SHA343f6ce4e3c05d319222edb78a32eb9b7edf63aebbe5480f662be2964a8f21ad、archive SHAfc0b8cb2a85221bc61e5b4b30fd258d772cd88327dfff57337084c3a00be0a45を実照合。41member中必要11memberをstream読取/hash照合し、原rawの全複製はしていない。127ラベルはGit3061661/SHA0c63b9eb1450d824c45786c3c73aec62f0908f87d4d14f14eacaefed7b8adc26へbindした。

独自checkerは保存Actionを認証済み集合へ照合し、Label_verdictを判定に使わない。共有RuleAを参照してprefixを合法replayし、key/history/手番/局面と648featuresを照合した。127の全depth2認証再列挙は0であり、証明集合の正しさは127の有限受入れを継承する。ルールの独立実装ではない。数値・棋譜をNode VMで保存解析した今回を、新browser/AI機能成功とは呼ばない。

| 入力 | 認証適合手／全合法手 | A backup/CP NN | B backup/CP NN | S backup/CP NN | 採用手 |
| --- | ---: | ---: | ---: | ---: | --- |
| own-near-goal | 1/132 | 48/4 | 62/4 | 1/1 | pawn(0,+1)、即goal |
| opponent-threat | 2/131 | 10/9 | 10/10 | 1/1 | H(3,0)、次手goal回避 |
| both-near | 1/132 | 59/3 | 63/7 | 1/1 | pawn(0,+1)、即goal |
| wall-protected-threat | 124/124 | 10/10 | 14/14 | 1/1 | pawn(0,+1)、全合法safe |

全12公開でinput/key/history/seed1979、generation/epoch/request token、完成CP→SAB sequence→public Action、UTF8 body/不変性、合法集合との対応を確認した。通常A4/B4、S4は別。初回無し・late・公開enginefault・未完了・未実施は保存行/summary上0。私的STALE_GENERATION6件、明示discard4件、手NN−採用CP NN差6件を別に再計算し、公開fault0を私的エラーから変更しない。

通常backup276＝採用CP NN61＋terminal-noNN215。S backup4/NN4。手NN71＝通常67＋S4、採用CP NN総65との差6。startup6は別で、手＋startupは77。candidate edge和=sim−1、reference edge和=sim/root_visits=sim+1を照合し、candidate rootNはsource規約による値として扱った。candidate真parentQは欠測のまま。samebackupをsameNN/CPUへ変換しない。各入力のA/B/S初回648bits・136logits＋valueは一致、finite/strict[-1,1]を確認した。動的4入力に固定golden NN参照はなく、深部の全モデル一致は未確認。

S4はsim上限1、1backup/1NN、root edge全訪問0、完成publication1/sequence1、明示discard0。Worker zeroが予定採用より前で、完成CPは採用まで保持される。選ばれた手は4件すべて最大合法priorの手だった。必要served main/Worker等5scriptのhashは原保存bindingに一致し、必要7sourceは測定Gitと同bytes。Sだけsim上限を変えるadapter、通常規約の維持、receiverがCP Actionを合法Actionへ写像して採用する経路、budget stopが完成fieldsを消さないSAB実装を確認した。私的結果からreceiverが新しい手を選び直した根拠はない。

この結果が示すのは、当該モデルのroot priorが2即goalと1防御選択をすでに通し、1全合法safe対照は任意合法手を通すこと。root1の強い予算差でも採用Actionが全同じで、通常追加探索の利益をこの4例は識別しない。一方、非自明防御2手への適合は実際の有限能力を支え、全passを無価値とは呼ばない。安全回帰用の保存例としては有用だが、これを横に増やすだけでは長期手品質の改善検出を保証しない。

最小次案は、探索用と明記した別の小集合で、即goalを除き、複数手先の認証可能な選択に対してroot1と通常が異なる評価になるかを一度校正すること。費用を抑えるため既保存の失敗分岐を候補とし、深さ/node上限・未解決扱い・採点集合を新AI結果前に固定する。AI差が出なければ尺度変更、差が出ればその局面で採用量と手品質の対応を調べる。過去結果で選んだ探索集合の選定偏りを保持し、正式holdoutにしない。今回この案を実行せず、130を待つgateにもしていない。

500/402/予定411のidentityを照合し、全12最終stampは500ms内（最大416.625ms）、全12Worker停止upper<=D、通常6/8採用がACK受信より前。公開後新内部API開始の確実観測0は保存clock区間による有限分類。APIawait・Worker停止・ACKwallを内核CPUや実効思考時間へ読み替えない。予定411msと実timerを分けると、9件が予定より早く、最小差−0.729980ms、最大＋5.515137ms。実公開も9件が411msより早い。現在のdeadline内採用を反証しないが、厳密な411ms採用時刻保証は成立していない。途中drift・exact Atomic store・root準備span・CPU等値は未保証。

原両Modeldrop handles/activeNN0、各searchACK zero、main timer/message0、monitor全callback wait、inner forced controlledwait/残0とouter sole-root/subreaper同identitywait/remainingunknown0を別照合。原owner55と今回必要process再抽出59identityは別分母、現在同identity不在を確認した。自然終了・全期間遵守への格上げはしない。必要原入力/sourceのhashafter一致を固定した。

自己helperはTMP親directory未作成の起動前失敗1（子未開始）、予定timer以上を不当に必須としたchecker失敗1を保存した。後者は原9件の早timerが反証し、符号付き予定差を記録する修正後NN0再照合に成功した。原source/raw/条件を変えていない。管理childは全回収、CPU[0]単logical/currentRSS peak110,526,464B、資源guard違反0。短い読取・通信のPID/RSS・40ms瞬間peak/終了子CPUは未保証。新保存2MiB目安/既critic128MiB内、combined112MiBには未確認量を保守85MiB＋新2MiBとして計上し予約追加0。

本文前の自己source/child停止、全失敗、command・PID/starttick・前後hash・archive復元は [131保存正本](../../research-data/ai-sigma/131-tactical-saved-independent/archive-manifest.json) と [自己停止](../../research-data/ai-sigma/131-tactical-saved-independent/runtime-source-stopped-before-report.json) に保存。再現は `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 60s taskset -c 0 python3 -B tools/ai-sigma-tactical-saved-independent/runner.py --config <config> python3 -B <check.py>`。終了後Git保存/復元確認、Beads backup/reportでcoordinatorへ渡す。本人のみ受入れ待ち、goal/他者close0、actual_go=false。
