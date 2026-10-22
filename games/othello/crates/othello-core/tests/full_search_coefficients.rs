// SPDX-License-Identifier: GPL-3.0-or-later
// Original Console7.8.1 MPC coefficients, Takuto Yamana / upstream contributors.
use othello_core::full_search::MpcCoefficients;

#[test]
fn full_search_coefficients_json_roundtrip_preserves_bits() {
    let defaults = MpcCoefficients::default();
    assert_eq!(defaults.g.to_bits(), 0x3ffc_70a5_45d5_35a4);
    let original_decimal_json = r#"{
        "a": 0.7308488452189136,
        "b": -4.5708322989025865,
        "c": 1.096319765006055,
        "d": -0.8362251801219095,
        "e": 4.610017383697701,
        "f": 3.818582623595395,
        "g": 1.7775013664098447
    }"#;
    let serialized_defaults = serde_json::to_string(&defaults).expect("serialize public defaults");
    for (boundary, json) in [
        ("serialized defaults", serialized_defaults.as_str()),
        ("original decimal JSON", original_decimal_json),
    ] {
        let parsed: MpcCoefficients =
            serde_json::from_str(json).expect("parse public coefficients");
        let encoded = serde_json::to_string(&parsed).expect("reserialize public coefficients");
        let roundtrip: MpcCoefficients =
            serde_json::from_str(&encoded).expect("reparse public coefficients");
        // Parameter identity is bit-exact, independently of whether a search
        // enables MPC. The observed adjacent g value ends in35a5, not35a4.
        for (field, expected, decoded, repeated) in [
            ("a", defaults.a, parsed.a, roundtrip.a),
            ("b", defaults.b, parsed.b, roundtrip.b),
            ("c", defaults.c, parsed.c, roundtrip.c),
            ("d", defaults.d, parsed.d, roundtrip.d),
            ("e", defaults.e, parsed.e, roundtrip.e),
            ("f", defaults.f, parsed.f, roundtrip.f),
            ("g", defaults.g, parsed.g, roundtrip.g),
        ] {
            assert_eq!(
                decoded.to_bits(),
                expected.to_bits(),
                "{boundary}.{field}: original parse must preserve every coefficient bit"
            );
            assert_eq!(
                repeated.to_bits(),
                expected.to_bits(),
                "{boundary}.{field}: repeated JSON roundtrip must preserve every coefficient bit"
            );
        }
    }
}
