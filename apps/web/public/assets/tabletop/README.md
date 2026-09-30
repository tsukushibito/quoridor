# Tabletop assets

These selected runtime assets are stored locally and served beneath Vite's base path.
The browser does not contact Poly Haven or an image generation service.

## Comfy Café

- File: `comfy-cafe-2k.hdr` (2048 × 1024, Radiance HDR, 6,260,522 bytes).
- Source: [Poly Haven / Comfy Café](https://polyhaven.com/a/comfy_cafe).
- Photographer: Sergej Majboroda.
- License: [CC0](https://polyhaven.com/license); redistribution is permitted.
- Download: <https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/comfy_cafe_2k.hdr>.
- Download date: 2026-09-30. Poly Haven API MD5 verified: `e8d670a951dcbb06c0bb1d3a7b351f15`.
- Original bytes retained. Used as both the visible environment and the source of PMREM lighting/reflections.

## Generated beech albedo

- File: `beech-albedo.png`.
- Generated on 2026-09-30 with the built-in `image_gen` tool, then copied without content edits.
- This is an appearance reference for fine-grained hardwood, not a claim that Gigamic uses beech.
- The same selected grain image is tinted for board stain, wall wood, pawn paint and table wood.
- Roughness/fine bump are independent procedural microfibers, not measured PBR data.
- Full generation prompt and verification: [tabletop rendering report](../../../../../docs/reports/tabletop-rendering.md).

Unused generated variants and downloaded product reference photographs are not runtime assets.
