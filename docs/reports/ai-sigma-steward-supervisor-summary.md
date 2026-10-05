# 106 監督summaryの依存参照

旧run1b43dba5のsnapshot842,472Bを保存読取し、依存オブジェクトが親goalのdescription/全notesを繰返し埋め込むことを確認。issue_summaryのnotes_tailをdependenciesが迂回していた。約209,667tokens/切断は旧監督の報告値であり、今回tokenizerで再計算していない。

依存をid/issue_id/depends_on_id・type/dependency_type・status/assignee/labelsの参照へ正規化。説明/notes/再帰dependenciesをモデルsummaryへ複製しない。wrapper raw・旧snapshot/Git・追加inspectとnamespace拒否・選択/状態/許可判定は不変。

少数fixture＋実raw保存読取の5確認と構文pass。依存ID/関係・現在選択集合・notes_tailを維持。モデルstdout同じJSON直列化で838,665→24,891B（約97.0%減）、新snapshot27,768B。pause/未知owner/絶対期限拒否、自己短期child timeout/reapedを確認。旧raw hash不変。詳細: research-data/ai-sigma/106-supervisor-summary/verification.json、再現は同ディレクトリ記録のsnapshot参照に対しverify.py --summary-only --snapshot <path> --output <新自己出力先>。

92は旧owned完了/ownedなし・監督idle・正確identityを確認し、監視を秩序停止してからsource3fileを固定。guard期待hashだけ変更しvalidate→同runtime start→実reloaded04:46:09/loaded hash確認。現在scheduler2080724/start16927236、monitor2081005/start16928052、24hash不一致0。再開後の監視source編集0、旧104異常履歴を保持。config/contract/prompt・周期1200/turn180/end05:44:12は不変、active数拒否再導入0。main client/common/role/registry・103/105変更停止0。

短期child/source書込停止、意図的長期2PIDと92の05:39:12重job通知/05:44:12正確owned停止/05:47:12monitor回収/05:49:12保存責任を保持。次自然点検1回のsummary bytes、読取負担、notes/self-stop完了を40/92で追う。今回の静的比較/loadedを未来whole-turn成功・棋力改善と認定しない。新保存2MiB目安内、current RSSと瞬間peak/全hostの限界を区別。

運用/短期停止根拠: .artifacts/ai-sigma/resume-20261002/SUPERVISOR-SUMMARY/。Git版と受入れはBeads 106 notesを参照。統括受入れ待ち。
