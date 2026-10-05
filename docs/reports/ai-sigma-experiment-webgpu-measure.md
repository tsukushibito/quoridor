# EXPERIMENT_REPORT SIGMA-WEBGPU-MEASURE / quoridor-4lc.115

枠8・契約1。**現環境の物理WebGPU実行は未成立。実ブラウザのsoftware computeは支持、モデル数値・費用・探索評価回数は未実施。** actual_go=false、対局/holdout/学習0。受領10:24:17UTC、115のみ本人claim。処理11:24:17/新run11:19:17/提出11:34:17を維持し、早期に不足を返す。

Chromium149の既定/Vulkan指定2profileでsecure context・crossOriginIsolated・SAB/Atomicsを確認。compute sentinelは両方[7,11,23,35]を読戻したが、adapterはGoogle/SwiftShader/isFallbackAdapter=true、CDPもSwANGLE。物理RTX3060のVRAM約1501MiBは監視できるが、このdispatchやモデルGPU実行の証拠ではない。/dev/dxgは存在する。システムVulkanはvkCreateInstance=-9(VK_ERROR_INCOMPATIBLE_DRIVER)、標準ICD設定は空、container NVIDIA capabilityはcompute,utility。これは観測した経路の不足であり、GPU一般の性能負例ではない。

ORT-Web1.21.0の既package/exportと公式npm metadata/integrity/配布URLを確認した。同版WebGPU bundleの自域取得は許可済みだが、物理driver条件が未成立なので取得・モデルloadへ進まなかった。旧取得禁止が停止理由ではない。必要な次条件は物理GPU対応graphics/Vulkan経路の露出、non-software adapter/実compute/VRAM再確認、その後の同版asset整合とモデルprovider/fallback検査。共有環境変更は実施していない。Chromiumのdriver/起動条件は[公式説明](https://developer.chrome.com/blog/supercharge-web-ai-testing)、ORTのWebGPU入口は[公式説明](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html)を参照した。

全5runを区別。r1は相対command pathの検査器不具合。r2はChromium TIDのaffinity変更によるguardと、回収中の同検査再例外でlauncher停止記録が欠けた。失敗を保持し、owned TIDだけCPU2へ再pinする修正を行った。r3/r4は正常終了・device/buffer解放/monitor callback待ち/inner controlledPID0/outer wait remaining・unknown0。r5はCPU0のnative driver/公式metadata読取。r2は現在不在のみ、当時outerwait完了や自然終了へ格上げしない。

モデルload/NNは0。予定60call(warm12/steady48)・12検索は全未開始、startup/数値gateも未開始。software sentinel時間をNN費用比較へ流用しない。観測current RSS最大1,350,107,136B、RAM guard5.5GiB内。r3のowned TIDでCPU0 affinityを1件観測しCPU2へ再pinしたため、全期間CPU2保証はしない。r2の実wall欠測は総予算に600秒を保守課金し、既知browser runと合わせ612.951秒<1800、静的managed wall0.431秒。初期短command/瞬間peak/背景/物理VRAMのprocess帰属には限界がある。RAMとVRAMを混同しない。

本文前停止正本SHA `507ced1b7ec8c1dfbe8d8c1e29c10ab8561d3a5083744add82c8a162ca5d9b7d`、記録union122同identity現在不在。停止source Git `f575b6bf9172b5b49a60d739476612a6041a00d2`。元ONNX/Wasm/package hashは前後一致。r3のconfig Git欄は旧baseline残存、実started/inputSHAを正本とし元bytesは変更しない。r5の未追跡helperは実inputSHAと最終Git同bytesで特定した。

[要約](../../research-data/ai-sigma/115-webgpu-measure/summary.json)・[復元manifest](../../research-data/ai-sigma/115-webgpu-measure/manifest.json)・[全必要データarchive](../../research-data/ai-sigma/115-webgpu-measure/webgpu115-preflight.tar.gz)。76memberをstream復元hash一致確認、archive194408B。元失敗・全分母/command/PID/時計/監視/停止を保持。自己保存・Git/tempは既entry予約内、全host保存/全期間遵守の完全証明ではない。coordinator受入れ待ち。H1数値不一致/速度negative・棋力・正式公平性/NI/Sigma同等は認定しない。旧112/113・CPU/WDLは変更/統合しない。
