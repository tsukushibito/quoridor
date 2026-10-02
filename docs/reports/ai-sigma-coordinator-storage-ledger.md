# 99保存整理後の台帳更新

2026-10-02T03:39:24.025595+00:00、coordinator。99/99.1のroot受入れ・本人closeを継承。研究Git6710b17の75archiveと復元検査/保護対象、報告1b889414を参照し、全データ再検証/新保存writerは起動しない。旧結果・失敗・過去peakは変更しない。

現在実量はresearch-data/ai-sigma全体70,512,640B、共有Git objects 96,247,808B（旧baseline 31,640,576B）。全Git増分64,607,232Bを保守的に移管へ帰属し、workingとの保持合計135,119,872B。512MiBの移管予約を136MiB=142,606,336Bへ縮小し、確認済み未使用376MiB=394,264,576Bを未配分へ返却した。保持物と予約未使用7,486,464Bを分け、保持実量を予約に追加して二重加算しない。差は全Gitの同時commitを含む限定計測で、retention専用の厳密寄与とは呼ばない。

既capacity-beforeと同じ保守式（旧未確認課金不変+全現artifacts+共有Git+既他予約envelope+今回移管envelope）を現在値で更新した。条件付き総額9,630,374,355B、12GiB上限内の未配分3,254,527,533B。旧基準との重複・共有cache欠測を保守計上したままで、全host一意byte/瞬間peakの全面保証ではない。旧削減概算1.572GBと未使用予約返却を別に記録する。上限12GiB/終了05:49:12を変更しない。

正本はresearch-data/ai-sigma/resource-ledger.json。100の新8MiBは既critic128MiB内、追加予約0。100は03:36:34同savedcriticへ実accepted、最大8公開/保存36算術、正式NI/対局0。現在の93/95展開pathは読取担当の終了確認後に通常整理できるが、このturnで削除0。過去rawはGit/archiveから必要分を展開する。
