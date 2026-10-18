// Serve o site de frontend/ em http://localhost:8000, a mesma origem que o
// Supabase já aceita para login (Redirect URLs: http://localhost:8000/**).
// Se a porta 8000 estiver ocupada (python -m http.server), feche-o antes.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

const PORTA: u16 = 8000;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_localhost::Builder::new(PORTA).build())
        .run(tauri::generate_context!())
        .expect("erro ao iniciar o Mapa da Bíblia");
}
