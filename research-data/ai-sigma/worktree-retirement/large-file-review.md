# 未一致上位の実読補足

rootはlegacy-preaction-catalogの必要範囲だけ読取り。未一致上位にSIGMA-WEB-PORT/build/target以下のserde rlib/rmeta（各約5MB）、analysis/SIGMA-ROOT-SELECTION-ABLATION/diagnostic約4.55MB、reference/SIGMA-WEB-REFERENCE/ort-wasm-simd-threaded.jsep.wasm約23.9MBが含まれる点を確認しました。前2は私有再生成物の候補、最後は固定依存版/取得情報と必要再現経路を確認する候補です。receipt/観測ではないこれらを無条件の新Git保存対象にせず、非使用・source/lock/command等の根拠で分類してください。分類と削除はStewardの単独所有のまま、rootは原本/分類catalogを編集・削除していません。
