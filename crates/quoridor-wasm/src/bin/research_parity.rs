fn main() {
    let input =
        std::fs::read_to_string(std::env::args().nth(1).expect("golden input path")).unwrap();
    println!(
        "{}",
        quoridor_wasm::research::diagnose(&input).expect("research diagnostic")
    );
}
