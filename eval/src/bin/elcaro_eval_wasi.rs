//! WASI binary entry point for the Elcaro eval — the Wasmer track.
//!
//! The same scoring engine the Telegraph validators call through the
//! pointer/length ABI, exposed as a plain stdin→stdout program so it runs
//! under any WASI runtime (`wasmer run`, `@wasmer/sdk`, wasmtime).
//!
//!   echo '<miner responses JSON>' | wasmer run elcaro_eval_wasi.wasm
//!   wasmer run elcaro_eval_wasi.wasm -- --corpus   # dump the test corpus
//!
//! Named `_wasi` on purpose: the lib target is a `cdylib` that also emits
//! `elcaro_eval.wasm`, and two targets writing one filename is a cargo
//! collision whose winner is not defined. The browser/Telegraph artifact
//! stays `elcaro_eval.wasm`; this one is unambiguously the WASI command.
//!
//! Build:
//!   rustup target add wasm32-wasip1
//!   cargo build --release --target wasm32-wasip1 --bin elcaro_eval_wasi

use std::io::{Read, Write};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--corpus") {
        print!("{}", elcaro_eval::get_test_cases());
        return;
    }

    let mut input = String::new();
    if std::io::stdin().read_to_string(&mut input).is_err() {
        eprintln!("elcaro_eval: failed to read responses JSON from stdin");
        std::process::exit(2);
    }

    let result = elcaro_eval::evaluate(&input);
    let _ = std::io::stdout().write_all(result.as_bytes());
    let _ = std::io::stdout().write_all(b"\n");
}
