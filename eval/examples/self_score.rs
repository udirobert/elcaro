use std::env;
use std::fs;

/// Usage: cargo run --example self_score -- <responses.json>
/// Prints the EvalResult JSON from evaluate() to stdout.
fn main() {
    let path = env::args().nth(1).expect("usage: self_score <responses.json>");
    let json = fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {}: {}", path, e));
    let result = elcaro_eval::evaluate(&json);
    println!("{}", result);
}
