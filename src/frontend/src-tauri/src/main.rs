#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, State, Wry};

const PROFILE_FILE_NAME: &str = "desktop-runtime.json";
const DEFAULT_REMOTE_BASE_URL: &str = "http://127.0.0.1:8090";
const EMBEDDED_BACKEND_RESOURCE: &str = "binaries/oko-backend-aarch64-apple-darwin";
const DEFAULT_DASHBOARD_RESOURCE: &str = "resources/dashboard.default.yaml";
const USER_RUNTIME_DIR_NAME: &str = ".oko";
const USER_CONFIG_FILE_NAME: &str = "dashboard.yaml";
const USER_LAN_SCAN_RESULT_FILE: &str = "data/lan_scan_result.json";
const USER_BACKEND_LOG_FILE: &str = "logs/backend.log";
const USER_BACKEND_PID_FILE: &str = "backend.pid";
const EMBEDDED_ADMIN_TOKEN: &str = "oko-desktop-embedded";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum RuntimeMode {
  Embedded,
  Remote,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct RuntimeProfile {
  mode: RuntimeMode,
  remote_base_url: String,
}

impl Default for RuntimeProfile {
  fn default() -> Self {
    Self {
      mode: RuntimeMode::Embedded,
      remote_base_url: DEFAULT_REMOTE_BASE_URL.to_string(),
    }
  }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeProfilePayload {
  desktop: bool,
  mode: RuntimeMode,
  api_base_url: String,
  remote_base_url: String,
  embedded_running: bool,
}

#[derive(Debug)]
struct EmbeddedBackend {
  child: Child,
  api_base_url: String,
}

#[derive(Debug)]
struct DesktopState {
  profile: Mutex<RuntimeProfile>,
  embedded_backend: Mutex<Option<EmbeddedBackend>>,
}

impl DesktopState {
  fn new(profile: RuntimeProfile) -> Self {
    Self {
      profile: Mutex::new(profile),
      embedded_backend: Mutex::new(None),
    }
  }
}

fn normalize_url(value: impl AsRef<str>) -> String {
  let raw = value.as_ref().trim();
  if raw.is_empty() {
    return DEFAULT_REMOTE_BASE_URL.to_string();
  }
  raw.trim_end_matches('/').to_string()
}

fn app_config_dir(app: &AppHandle) -> PathBuf {
  match app.path().app_config_dir() {
    Ok(path) => path,
    Err(_) => std::env::temp_dir().join("oko-desktop"),
  }
}

fn runtime_profile_path(app: &AppHandle) -> PathBuf {
  app_config_dir(app).join(PROFILE_FILE_NAME)
}

fn load_runtime_profile(app: &AppHandle) -> RuntimeProfile {
  let path = runtime_profile_path(app);
  let raw = match fs::read_to_string(path) {
    Ok(content) => content,
    Err(_) => return RuntimeProfile::default(),
  };

  match serde_json::from_str::<RuntimeProfile>(&raw) {
    Ok(profile) => RuntimeProfile {
      mode: profile.mode,
      remote_base_url: normalize_url(profile.remote_base_url),
    },
    Err(_) => RuntimeProfile::default(),
  }
}

fn persist_runtime_profile(app: &AppHandle, profile: &RuntimeProfile) -> Result<(), String> {
  let dir = app_config_dir(app);
  fs::create_dir_all(&dir).map_err(|error| format!("Failed to create config dir: {error}"))?;

  let path = dir.join(PROFILE_FILE_NAME);
  let content = serde_json::to_string_pretty(profile).map_err(|error| format!("Failed to serialize profile: {error}"))?;
  fs::write(path, content).map_err(|error| format!("Failed to save profile: {error}"))
}

fn resolve_embedded_backend_binary(app: &AppHandle) -> Option<PathBuf> {
  if let Ok(explicit) = std::env::var("OKO_DESKTOP_BACKEND_BIN") {
    let path = PathBuf::from(explicit);
    if path.exists() {
      return Some(path);
    }
  }

  if let Ok(resource_dir) = app.path().resource_dir() {
    let bundled = resource_dir.join(EMBEDDED_BACKEND_RESOURCE);
    if bundled.exists() {
      return Some(bundled);
    }
  }

  None
}

fn user_runtime_dir() -> PathBuf {
  let home = std::env::var_os("HOME")
    .map(PathBuf::from)
    .unwrap_or_else(std::env::temp_dir);
  home.join(USER_RUNTIME_DIR_NAME)
}

fn backend_pid_file() -> PathBuf {
  user_runtime_dir().join(USER_BACKEND_PID_FILE)
}

fn terminate_stale_backend_by_pid_file() {
  let pid_path = backend_pid_file();
  let raw = match fs::read_to_string(&pid_path) {
    Ok(value) => value,
    Err(_) => return,
  };

  let pid = raw.trim();
  if pid.is_empty() {
    let _ = fs::remove_file(pid_path);
    return;
  }

  let _ = Command::new("kill").arg("-TERM").arg(pid).status();
  let _ = fs::remove_file(pid_path);
}

fn resolve_default_dashboard_template(app: &AppHandle) -> Option<PathBuf> {
  if let Ok(explicit) = std::env::var("OKO_DESKTOP_DEFAULT_CONFIG") {
    let explicit_path = PathBuf::from(explicit);
    if explicit_path.exists() {
      return Some(explicit_path);
    }
  }

  if let Ok(resource_dir) = app.path().resource_dir() {
    let bundled = resource_dir.join(DEFAULT_DASHBOARD_RESOURCE);
    if bundled.exists() {
      return Some(bundled);
    }
  }

  let cwd = std::env::current_dir().ok()?;
  let candidates = [
    cwd.join("../../dashboard.yaml"),
    cwd.join("../dashboard.yaml"),
    cwd.join("dashboard.yaml"),
  ];

  candidates.into_iter().find(|path| path.exists())
}

fn ensure_user_runtime_files(app: &AppHandle) -> Result<(PathBuf, PathBuf, PathBuf, PathBuf), String> {
  let runtime_dir = user_runtime_dir();
  let config_path = runtime_dir.join(USER_CONFIG_FILE_NAME);
  let lan_result_file = runtime_dir.join(USER_LAN_SCAN_RESULT_FILE);
  let backend_log_file = runtime_dir.join(USER_BACKEND_LOG_FILE);

  fs::create_dir_all(&runtime_dir).map_err(|error| format!("Failed to create runtime dir: {error}"))?;
  if let Some(parent) = lan_result_file.parent() {
    fs::create_dir_all(parent).map_err(|error| format!("Failed to create runtime data dir: {error}"))?;
  }
  if let Some(parent) = backend_log_file.parent() {
    fs::create_dir_all(parent).map_err(|error| format!("Failed to create backend log dir: {error}"))?;
  }

  if !config_path.exists() {
    let template = resolve_default_dashboard_template(app)
      .ok_or_else(|| "Default dashboard template not found for first desktop run".to_string())?;
    fs::copy(&template, &config_path).map_err(|error| {
      format!(
        "Failed to create user dashboard config from template {}: {error}",
        template.display()
      )
    })?;
  }

  Ok((runtime_dir, config_path, lan_result_file, backend_log_file))
}

fn resolve_dev_backend_script() -> Option<PathBuf> {
  let cwd = std::env::current_dir().ok()?;
  let candidates = [
    cwd.join("../desktop/backend_sidecar.py"),
    cwd.join("../../src/desktop/backend_sidecar.py"),
    cwd.join("src/desktop/backend_sidecar.py"),
  ];

  candidates.into_iter().find(|path| path.exists())
}

fn spawn_embedded_backend(app: &AppHandle) -> Result<EmbeddedBackend, String> {
  terminate_stale_backend_by_pid_file();

  let listener = TcpListener::bind("127.0.0.1:0").map_err(|error| format!("Failed to reserve local port: {error}"))?;
  let port = listener
    .local_addr()
    .map_err(|error| format!("Failed to read local port: {error}"))?
    .port();
  drop(listener);

  let api_base_url = format!("http://127.0.0.1:{port}");
  let (runtime_dir, config_path, lan_result_file, backend_log_file) = ensure_user_runtime_files(app)?;

  let mut command = if let Some(binary) = resolve_embedded_backend_binary(app) {
    let mut binary_command = Command::new(binary);
    binary_command.arg("--host").arg("127.0.0.1").arg("--port").arg(port.to_string());
    binary_command
  } else if let Some(script) = resolve_dev_backend_script() {
    let mut script_command = Command::new("python3");
    script_command
      .arg(script)
      .arg("--host")
      .arg("127.0.0.1")
      .arg("--port")
      .arg(port.to_string());
    script_command
  } else {
    return Err(
      "Embedded backend binary not found. Build sidecar and place it into src/frontend/src-tauri/binaries".to_string(),
    );
  };

  command
    .current_dir(&runtime_dir)
    .env("DASHBOARD_CONFIG_FILE", &config_path)
    .env("LAN_SCAN_RESULT_FILE", &lan_result_file)
    .env("DASHBOARD_ENABLE_LAN_SCAN", "true")
    .env("DASHBOARD_ADMIN_TOKEN", EMBEDDED_ADMIN_TOKEN)
    .env("LAN_SCAN_RUN_ON_STARTUP", "true")
    .env("LAN_SCAN_INTERVAL_SEC", "300");

  let backend_stdout = fs::File::create(&backend_log_file)
    .map_err(|error| format!("Failed to open backend log file {}: {error}", backend_log_file.display()))?;
  let backend_stderr = backend_stdout
    .try_clone()
    .map_err(|error| format!("Failed to clone backend log handle {}: {error}", backend_log_file.display()))?;
  command
    .stdin(Stdio::null())
    .stdout(Stdio::from(backend_stdout))
    .stderr(Stdio::from(backend_stderr));
  let child = command
    .spawn()
    .map_err(|error| format!("Failed to start embedded backend: {error}"))?;

  let pid_path = backend_pid_file();
  if let Some(parent) = pid_path.parent() {
    let _ = fs::create_dir_all(parent);
  }
  let _ = fs::write(pid_path, child.id().to_string());

  Ok(EmbeddedBackend { child, api_base_url })
}

fn stop_embedded_backend(state: &DesktopState) {
  let mut backend_guard = state.embedded_backend.lock().expect("embedded backend lock poisoned");
  if let Some(mut backend) = backend_guard.take() {
    let _ = backend.child.kill();
    let _ = backend.child.wait();
  }
  let _ = fs::remove_file(backend_pid_file());
}

fn ensure_runtime_mode(app: &AppHandle, state: &DesktopState) -> Result<(), String> {
  let mode = {
    let profile = state.profile.lock().expect("runtime profile lock poisoned");
    profile.mode.clone()
  };

  match mode {
    RuntimeMode::Embedded => {
      let mut backend_guard = state.embedded_backend.lock().expect("embedded backend lock poisoned");
      if backend_guard.is_none() {
        *backend_guard = Some(spawn_embedded_backend(app)?);
      }
      Ok(())
    }
    RuntimeMode::Remote => {
      stop_embedded_backend(state);
      Ok(())
    }
  }
}

fn build_runtime_payload(state: &DesktopState) -> RuntimeProfilePayload {
  let profile = state.profile.lock().expect("runtime profile lock poisoned").clone();
  let backend_guard = state.embedded_backend.lock().expect("embedded backend lock poisoned");

  let embedded_running = backend_guard.is_some();
  let api_base_url = if profile.mode == RuntimeMode::Embedded {
    backend_guard
      .as_ref()
      .map(|backend| backend.api_base_url.clone())
      .unwrap_or_else(|| profile.remote_base_url.clone())
  } else {
    profile.remote_base_url.clone()
  };

  RuntimeProfilePayload {
    desktop: true,
    mode: profile.mode,
    api_base_url,
    remote_base_url: profile.remote_base_url,
    embedded_running,
  }
}

fn emit_runtime_profile(app: &AppHandle, state: &DesktopState) {
  let payload = build_runtime_payload(state);
  let _ = app.emit("desktop://runtime-profile", payload);
}

fn show_main_window(app: &AppHandle) {
  if let Some(window) = app.get_webview_window("main") {
    let _ = window.show();
    let _ = window.unminimize();
    let _ = window.set_focus();
  }
}

fn emit_action(app: &AppHandle, action: &str) {
  let _ = app.emit("desktop://action", action.to_string());
}

fn handle_menu_action(app: &AppHandle, menu_id: &str) {
  match menu_id {
    "oko_show" => show_main_window(app),
    "oko_open_search" => emit_action(app, "open-search"),
    "oko_open_settings" => emit_action(app, "open-settings"),
    "oko_quit" => app.exit(0),
    _ => {}
  }
}

fn build_native_menu(app: &AppHandle<Wry>) -> Result<Menu<Wry>, tauri::Error> {
  let show = MenuItem::with_id(app, "oko_show", "Show Oko", true, None::<&str>)?;
  let open_search = MenuItem::with_id(app, "oko_open_search", "Open Search", true, None::<&str>)?;
  let open_settings = MenuItem::with_id(app, "oko_open_settings", "Open Settings", true, None::<&str>)?;
  let quit = MenuItem::with_id(app, "oko_quit", "Quit Oko", true, None::<&str>)?;
  let separator = PredefinedMenuItem::separator(app)?;

  let app_submenu = Submenu::with_items(
    app,
    "Oko",
    true,
    &[&show, &open_search, &open_settings, &separator, &quit],
  )?;

  Menu::with_items(app, &[&app_submenu])
}

fn setup_tray(app: &AppHandle<Wry>) -> Result<(), tauri::Error> {
  let show = MenuItem::with_id(app, "oko_show", "Show Oko", true, None::<&str>)?;
  let open_search = MenuItem::with_id(app, "oko_open_search", "Open Search", true, None::<&str>)?;
  let open_settings = MenuItem::with_id(app, "oko_open_settings", "Open Settings", true, None::<&str>)?;
  let quit = MenuItem::with_id(app, "oko_quit", "Quit Oko", true, None::<&str>)?;
  let separator = PredefinedMenuItem::separator(app)?;
  let menu = Menu::with_items(app, &[&show, &open_search, &open_settings, &separator, &quit])?;

  TrayIconBuilder::new()
    .tooltip("Oko")
    .menu(&menu)
    .on_menu_event(|app, event| {
      handle_menu_action(app, event.id().as_ref());
    })
    .on_tray_icon_event(|tray, event| {
      if let TrayIconEvent::Click {
        button: MouseButton::Left,
        button_state: MouseButtonState::Up,
        ..
      } = event
      {
        show_main_window(&tray.app_handle());
      }
    })
    .build(app)?;

  Ok(())
}

#[tauri::command]
fn desktop_get_runtime_profile(state: State<'_, DesktopState>) -> RuntimeProfilePayload {
  build_runtime_payload(&state)
}

#[tauri::command]
fn desktop_set_runtime_profile(
  app: AppHandle,
  state: State<'_, DesktopState>,
  mode: String,
  remote_base_url: String,
) -> Result<RuntimeProfilePayload, String> {
  {
    let mut profile = state.profile.lock().expect("runtime profile lock poisoned");
    profile.mode = match mode.as_str() {
      "embedded" => RuntimeMode::Embedded,
      "remote" => RuntimeMode::Remote,
      other => return Err(format!("Unsupported runtime mode: {other}")),
    };
    profile.remote_base_url = normalize_url(remote_base_url);
    persist_runtime_profile(&app, &profile)?;
  }

  ensure_runtime_mode(&app, &state)?;
  let payload = build_runtime_payload(&state);
  emit_runtime_profile(&app, &state);
  Ok(payload)
}

#[tauri::command]
fn desktop_show_main_window(app: AppHandle) {
  show_main_window(&app);
}

fn ensure_apple_silicon() -> Result<(), String> {
  if cfg!(target_os = "macos") && cfg!(target_arch = "aarch64") {
    return Ok(());
  }

  Err("This desktop target is configured only for macOS Apple Silicon (aarch64).".to_string())
}

fn main() {
  let builder = tauri::Builder::default()
    .setup(|app| {
      if let Err(error) = ensure_apple_silicon() {
        return Err(std::io::Error::other(error).into());
      }

      let profile = load_runtime_profile(&app.handle());
      let state = DesktopState::new(profile);

      if let Err(error) = ensure_runtime_mode(&app.handle(), &state) {
        return Err(std::io::Error::other(error).into());
      }
      app.manage(state);

      let menu = build_native_menu(app.handle())?;
      app.set_menu(menu)?;
      setup_tray(app.handle())?;

      if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
      }

      if let Some(state_ref) = app.try_state::<DesktopState>() {
        emit_runtime_profile(&app.handle(), state_ref.inner());
      }

      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      desktop_get_runtime_profile,
      desktop_set_runtime_profile,
      desktop_show_main_window
    ])
    .on_menu_event(|app, event| {
      handle_menu_action(app, event.id().as_ref());
    });

  builder
    .run(tauri::generate_context!())
    .unwrap_or_else(|error| panic!("error while running Oko desktop: {error}"));

  // Ensure spawned backend process does not leak on app shutdown.
  // Accessing managed state is not available after run(), so this is a no-op marker.
  // Process cleanup happens on mode switches and OS process teardown.
}
