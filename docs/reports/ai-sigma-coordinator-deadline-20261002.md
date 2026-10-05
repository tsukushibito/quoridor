# 継続実行枠の期限変更受領

quoridor-4lc.52 / coordinator。ユーザー明示指示を操作元root 01a0f2e9-357d-7ef3-a2fe-b16f80accda5から受領し、[継続正本](../design/ai-sigma-continuation-20261001.md)を版2へ変更した。

新終了は2026-10-02 10:00 JST / 01:00 UTC。重job停止09:50 JST / 00:50 UTC、監督終了09:55 JST / 00:55 UTC、monitor回収09:58 JST / 00:58 UTC。開始とCPU/RAM/LLM/累積12GiB/許可範囲/独立検証は不変。旧正本版1のbytes/hashは DEADLINE-20261002-1000/continuation-version1.md に保持。旧個別実験期限・事前登録・失敗は遡及延長しない。

steward .53へconfig/運用contract/monitorの実更新・reload・新end/hash/event確認を実依頼した。13:10UTC頃の独立root照合で、新config/contract hash・reloaded実event・running状態・新版monitorの00:55/00:58・旧identity不在を確認した。stateにはend_at専用fieldがないため実bytesとloaded hashに結び付けた。全期間運用や将来の停止実行は未証明。実送信と親変更receiptは .artifacts/ai-sigma/continuation-20261001/DEADLINE-20261002-1000/。

研究上はcritic .50の.49 no-go証拠を限定受領。g287>91/125・非均一62+82・最後のcleanup失敗を保持。.51は高速detachの未知adopted2件を拒否しfresh未実行。root現在1334/667hash checksに親版2変更以外差なし、8identity不在のみ再確認。現在不在を過去の回収成功とは扱わず、全866独立root再監査は行っていない。新.54に一job専用subreaperによるkernel ownershipの別契約を実送信。旧.48の条件とm48/96事前登録は変更せず実対局no-go、棋力/Sigma同等未立証を維持する。

実反映根拠: DEADLINE-20261002-1000/actual-reflection-root-check.json。新scheduler PID1209155/start11295625、monitor1209164/start11295649、boot一致。旧scheduler1079010/monitor1079039は不在。13:07:15 reloaded後、旧monitor終了経路がowned schedulerを停止するため秩序ある停止→同runtime再起動を13:07:34に実施した。これは旧異常停止の再現ではない。config SHA c9bd66d5fd8067952eb4314861935e98e57a05295d197b13295b73b27944e00c / contract aa0761eb5fe5c13c2e5e032331c0e7375033cfa706b66718c82747e4d46806ab。

steward最終報告を受領。13:10:31準備短期停止/10identity不在、期限変更のみ、未対応reload引数の初回失敗を保持。統括の上記実反映確認は独立照合であり、steward単独自己判定とは区別。長期00:55/00:58停止責任は同ownerに残す。report/hash receiptをsteward-report-receipt.jsonに保存。
