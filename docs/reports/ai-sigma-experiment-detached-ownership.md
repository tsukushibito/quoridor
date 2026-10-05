# SIGMA-DETACHED-OWNERSHIP / quoridor-4lc.51 / 試行1・契約1
experiment → coordinator。最終no-go。新copyのみ実装、旧.49 source/raw/時計g287>91/非uniform62+82はread-only保持。.49 close0、実対局/holdout/取得/build/GPU/委譲0。

Nodeの明示spawn・既知親からのscanでboot/PID/starttick/親子由来を台帳登録。外側subreaperはroot/親/boot/現在identityを検証しACKし、PGID変更後も登録済み同identityだけ監視・adoption waitする。ACK欠落/未知adoptedをsignal前に拒否。absence1000ms・共有drain100msを維持。

dummyで別session/PGID・TERM無視→KILL→自己adopted Z→wait→PID0、自然exit/既signalCode/idempotence、再利用token/未知親・adopted拒否、非所有dummyの除外と別owner回収、受領遅延/欠落、既transaction watchdogの公開破棄/fresh禁止を保存。負のreuseテストがACK未取得時の拒否を期待せず失敗したため、証拠保持・自己停止後にassertだけ一度修正。最終source dummyも成功。

同最終main/正tokenのfixedinitial5を一度だけ起動。正常candidate/reference2応答とT10 Action=nullの計3要求を保存。最初のcleanup前に未知adopted2件（1186567/11165088、1186570/11165091）を検出しUNKNOWN_ADOPTED_OWNERSHIP_REFUSED。高速detachの親子来歴を登録できず、fresh/残2要求/最終cleanupは未実施。8identityは登録できたが全所有集合の証明には不足。名称/profileから所有を推定せず、未知へのsignal/wait0、実NN再試行0。

12:49:30に本文前stop/source/input-afterを保存。全自己job終了、観測44identityと上記2件は現在不在。ただしmonitor remaining=[]/現在不在をcontrolled PID0成功へ救済しない。最終NN job終了時刻・PID/PGID/ACK/reapは詳細JSON。原入力552hash不変、worker/kernel/NN/rules/PUCT1.5Q0/T500g91不変。

観測peak RSS2062446592B、未知子RSS観測下限6680576B、新規logical3681700B（既entry予約内追加0）。観測owned全TID CPU2、未知子全期間RSS/CPU・瞬間peak・全期間遵守未確認。entry_ready/clock_gate/actual_go=false、.51独立受入れ待ちin_progress、source/NN停止。旧.43原因未確定/旧失敗保持、棋力・時計・採用認定0。詳細: SIGMA-DETACHED-OWNERSHIP/manifest-final.json、summary/resources/runtime-stopped/source.patch。
