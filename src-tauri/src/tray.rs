use std::sync::{atomic::Ordering, Mutex};
use tauri::{
    menu::{Menu, MenuItem},
    tray::{TrayIcon, TrayIconBuilder},
    Manager, Runtime, Wry,
};

pub struct TrayState {
    tray: TrayIcon<Wry>,
    toggle_item: MenuItem<Wry>,
}

pub fn setup(app: &tauri::App) -> tauri::Result<()> {
    let toggle_item = MenuItem::with_id(app, "toggle", "Start Recording", true, None::<&str>)?;
    let settings_item = MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
    let debug_item = MenuItem::with_id(app, "debug", "Debug Logs", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&toggle_item, &settings_item, &debug_item, &quit_item])?;

    let icon = app
        .default_window_icon()
        .cloned()
        .expect("app must have an icon configured in tauri.conf.json");

    let tray = TrayIconBuilder::new()
        .icon(icon)
        .tooltip("whisper-type")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "toggle" => handle_toggle(app),
            "settings" => {
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
            "debug" => {
                if let Some(win) = app.get_webview_window("debug") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .build(app)?;

    app.manage(Mutex::new(TrayState { tray, toggle_item }));

    // Fermer la fenêtre settings → hide() plutôt que quitter l'app.
    if let Some(win) = app.get_webview_window("main") {
        let win_clone = win.clone();
        win.on_window_event(move |event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = win_clone.hide();
            }
        });
    }

    Ok(())
}

fn handle_toggle<R: Runtime>(app: &tauri::AppHandle<R>) {
    let was_recording = match app.try_state::<crate::RecordingState>() {
        Some(s) => s.0.fetch_xor(true, Ordering::SeqCst),
        None => return,
    };
    if was_recording {
        set_transcribing(app);
    } else {
        set_recording(app);
    }
    let cmd = if was_recording { "stop" } else { "start" };
    if let Some(sc_state) = app.try_state::<crate::SidecarState>() {
        if let Some(sc) = sc_state.0.lock().unwrap().as_mut() {
            if let Err(e) = sc.send_cmd(cmd) {
                log::error!("tray toggle → sidecar '{cmd}' failed: {e}");
            }
        }
    }
}

pub fn set_idle<R: Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(ts) = app.try_state::<Mutex<TrayState>>() {
        let ts = ts.lock().unwrap();
        let _ = ts.toggle_item.set_text("Start Recording");
        let _ = ts.tray.set_tooltip(Some("whisper-type"));
    }
}

pub fn set_recording<R: Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(ts) = app.try_state::<Mutex<TrayState>>() {
        let ts = ts.lock().unwrap();
        let _ = ts.toggle_item.set_text("Stop Recording");
        let _ = ts.tray.set_tooltip(Some("whisper-type — recording..."));
    }
}

pub fn set_transcribing<R: Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(ts) = app.try_state::<Mutex<TrayState>>() {
        let ts = ts.lock().unwrap();
        let _ = ts.toggle_item.set_text("Transcribing...");
        let _ = ts.tray.set_tooltip(Some("whisper-type — transcribing..."));
    }
}
