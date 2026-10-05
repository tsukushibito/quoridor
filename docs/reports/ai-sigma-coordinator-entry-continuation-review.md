# ORT最終入口の独立検証への引渡し / quoridor-4lc.39 → .43

2026-10-01、継続枠版1/17:00UTC。experiment .39の最終manifest SHA83dcd87000818628099d7daec1c5730058a82439baa46cf894d6c235f1f2d04a、report SHAe3d3fb51d242444ebde79cbb4aa99746fcaec23f25ae7083a5ebf798a58ecf7aを固定。統括は38checks全hash一致とsource_write_stopped/actual_go=falseを確認した。writer190 PID/starttick不在は報告上の事実であり、独立確認はcriticへ依頼する。初回32/補足5/最終5は異なる版/目的で、42件を速度や標本に合算しない。

正診断token→同main実NN、既run拒否、型/取引/責任/最終stamp、bounded停止→freshが自己実行で報告された。旧zombie除外不足・分類漏れ・scope失敗、全session強制停止とT10 NN回数欠測は保持する。有限入口gateの報告を独立受入れ済・時計tail保証・棋力改善にしない。旧32局/未達、新実対局0を維持。

新子.43契約 docs/design/ai-sigma-contract-critic-entry-continuation.md SHAfc2a75d6974a7f56a81631c5eafa0882ab26721dbac2ad31a52818ac2803c9df。最終同mainの独立mock/少数golden、責任/取引/postvalidation stamp/無応答/zombie含む不在→freshを優先する。CPU2/RAM3 guard2.5、新128MiB guard112、処理受領35分以内または10:45/提出45分以内または10:55の早い方。旧input/成果/製品source/lockは読取のみ。独立入力不変と自己stopを文書より先に保存。準備受入れ後も新比較には別事前登録/校正/統括freezeが必要。

独立128MiBは現未配分から予約、条件付き残3,744,036,397B。steward .42の新32MiBは既存steward128MiB内で追加予約0。owner未確定増分と瞬間RSS/範囲外共有分の限界を保持し、正確全面残量と認定しない。全CPU4/RAM8/LLM3/累積12GiB、scheduler16:55/継続枠17:00を変更しない。競合A/B/CとH1backend/H2探索/H3時計・cp/H4標本を保持。

実依頼accepted=true、受領 2026-10-01T10:11:08.164429+00:00、critic turn 01a0f6f2-46e7-7960-af57-b7f175ceff6f。担当報告先coordinator。
