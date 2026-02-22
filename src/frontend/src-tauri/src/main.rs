#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, RunEvent, State, Wry};

const PROFILE_FILE_NAME: &str = "desktop-runtime.json";
const DEFAULT_REMOTE_BASE_URL: &str = "http://127.0.0.1:8090";
const EMBEDDED_BACKEND_RESOURCE: &str = "binaries/oko-backend-aarch64-apple-darwin";
const DEFAULT_DASHBOARD_RESOURCE: &str = "resources/dashboard.default.yaml";
const USER_RUNTIME_DIR_NAME: &str = ".oko";
const USER_CONFIG_FILE_NAME: &str = "dashboard.yaml";
const USER_BACKEND_DB_FILE: &str = "data/dashboard.sqlite3";
const USER_LAN_SCAN_RESULT_FILE: &str = "data/lan_scan_result.json";
const USER_BACKEND_LOG_FILE: &str = "logs/backend.log";
const USER_BACKEND_PID_FILE: &str = "backend.pid";

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

#[derive(Clone, Debug, Serialize, Deserialize)]
struct BackendPidRecord {
  pid: u32,
  #[serde(default)]
  started_at: Option<String>,
  #[serde(default)]
  command_hint: Option<String>,
}

fn read_backend_pid_record(pid_path: &PathBuf) -> Option<BackendPidRecord> {
  let raw = fs::read_to_string(pid_path).ok()?;

  if let Ok(record) = serde_json::from_str::<BackendPidRecord>(&raw) {
    if record.pid > 0 {
      return Some(record);
    }
    return None;
  }

  let legacy_pid = raw.trim().parse::<u32>().ok().filter(|value| *value > 0)?;
  Some(BackendPidRecord {
    pid: legacy_pid,
    started_at: None,
    command_hint: None,
  })
}

fn read_process_field(pid: u32, field: &str) -> Option<String> {
  let output = Command::new("ps")
    .arg("-p")
    .arg(pid.to_string())
    .arg("-o")
    .arg(field)
    .output()
    .ok()?;

  if !output.status.success() {
    return None;
  }

  let raw = String::from_utf8(output.stdout).ok()?;
  let value = raw.trim();
  if value.is_empty() {
    return None;
  }
  Some(value.to_string())
}

fn read_process_start_signature(pid: u32) -> Option<String> {
  read_process_field(pid, "lstart=")
}

fn read_process_command_line(pid: u32) -> Option<String> {
  read_process_field(pid, "command=")
}

fn command_hint_matches(command_line_lower: &str, command_hint: Option<&str>) -> bool {
  match command_hint {
    None => true,
    Some(value) if value.trim().is_empty() => true,
    Some(value) => {
      let hint_basename = PathBuf::from(value)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or(value)
        .to_lowercase();
      !hint_basename.is_empty() && command_line_lower.contains(&hint_basename)
    }
  }
}

fn is_embedded_backend_command(command_line: &str, command_hint: Option<&str>) -> bool {
  let command_line_lower = command_line.to_lowercase();
  let has_known_identity = command_line_lower.contains("oko-backend-aarch64-apple-darwin")
    || command_line_lower.contains("backend_sidecar.py");
  let has_expected_flags = command_line_lower.contains("--host")
    && command_line_lower.contains("127.0.0.1")
    && command_line_lower.contains("--port");

  has_known_identity
    && has_expected_flags
    && command_hint_matches(&command_line_lower, command_hint)
}

fn should_terminate_stale_backend(record: &BackendPidRecord) -> bool {
  let command_line = match read_process_command_line(record.pid) {
    Some(value) => value,
    None => return false,
  };

  if !is_embedded_backend_command(&command_line, record.command_hint.as_deref()) {
    return false;
  }

  match record.started_at.as_deref() {
    None => true,
    Some(expected_start) if expected_start.trim().is_empty() => true,
    Some(expected_start) => match read_process_start_signature(record.pid) {
      Some(actual_start) => actual_start == expected_start,
      None => false,
    },
  }
}

fn persist_backend_pid_record(pid_path: &PathBuf, record: &BackendPidRecord) {
  if let Some(parent) = pid_path.parent() {
    let _ = fs::create_dir_all(parent);
  }

  if let Ok(serialized) = serde_json::to_string(record) {
    let _ = fs::write(pid_path, serialized);
  } else {
    let _ = fs::write(pid_path, record.pid.to_string());
  }
}

fn terminate_stale_backend_by_pid_file() {
  let pid_path = backend_pid_file();
  let record = match read_backend_pid_record(&pid_path) {
    Some(value) => value,
    None => {
      let _ = fs::remove_file(pid_path);
      return;
    }
  };

  if !should_terminate_stale_backend(&record) {
    let _ = fs::remove_file(pid_path);
    return;
  }

  let _ = Command::new("kill").arg("-TERM").arg(record.pid.to_string()).status();
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

fn should_create_bootstrap_config(config_exists: bool, db_exists: bool) -> bool {
  !config_exists && !db_exists
}

fn ensure_user_runtime_files(app: &AppHandle) -> Result<(PathBuf, PathBuf, PathBuf, PathBuf, PathBuf), String> {
  let runtime_dir = user_runtime_dir();
  let config_path = runtime_dir.join(USER_CONFIG_FILE_NAME);
  let db_file = runtime_dir.join(USER_BACKEND_DB_FILE);
  let lan_result_file = runtime_dir.join(USER_LAN_SCAN_RESULT_FILE);
  let backend_log_file = runtime_dir.join(USER_BACKEND_LOG_FILE);

  fs::create_dir_all(&runtime_dir).map_err(|error| format!("Failed to create runtime dir: {error}"))?;
  if let Some(parent) = db_file.parent() {
    fs::create_dir_all(parent).map_err(|error| format!("Failed to create runtime DB dir: {error}"))?;
  }
  if let Some(parent) = lan_result_file.parent() {
    fs::create_dir_all(parent).map_err(|error| format!("Failed to create runtime data dir: {error}"))?;
  }
  if let Some(parent) = backend_log_file.parent() {
    fs::create_dir_all(parent).map_err(|error| format!("Failed to create backend log dir: {error}"))?;
  }

  if should_create_bootstrap_config(config_path.exists(), db_file.exists()) {
    let template = resolve_default_dashboard_template(app)
      .ok_or_else(|| "Default dashboard template not found for first desktop run".to_string())?;
    fs::copy(&template, &config_path).map_err(|error| {
      format!(
        "Failed to create user dashboard config from template {}: {error}",
        template.display()
      )
    })?;
  }

  Ok((runtime_dir, config_path, db_file, lan_result_file, backend_log_file))
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
  let (runtime_dir, config_path, db_file, lan_result_file, backend_log_file) = ensure_user_runtime_files(app)?;

  let (mut command, command_hint) = if let Some(binary) = resolve_embedded_backend_binary(app) {
    let hint = binary.to_string_lossy().to_string();
    let mut binary_command = Command::new(binary);
    binary_command.arg("--host").arg("127.0.0.1").arg("--port").arg(port.to_string());
    (binary_command, hint)
  } else if let Some(script) = resolve_dev_backend_script() {
    let hint = script.to_string_lossy().to_string();
    let mut script_command = Command::new("python3");
    script_command
      .arg(script)
      .arg("--host")
      .arg("127.0.0.1")
      .arg("--port")
      .arg(port.to_string());
    (script_command, hint)
  } else {
    return Err(
      "Embedded backend binary not found. Build sidecar and place it into src/frontend/src-tauri/binaries".to_string(),
    );
  };

  command
    .current_dir(&runtime_dir)
    .env("DASHBOARD_CONFIG_FILE", &config_path)
    .env("DASHBOARD_DB_FILE", &db_file)
    .env("LAN_SCAN_RESULT_FILE", &lan_result_file)
    .env("DASHBOARD_ENABLE_LAN_SCAN", "true")
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
  let pid_record = BackendPidRecord {
    pid: child.id(),
    started_at: read_process_start_signature(child.id()),
    command_hint: Some(command_hint),
  };
  persist_backend_pid_record(&pid_path, &pid_record);

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

fn embedded_backend_is_alive(backend: &mut EmbeddedBackend) -> bool {
  match backend.child.try_wait() {
    Ok(None) => true,
    Ok(Some(_)) => false,
    Err(_) => false,
  }
}

fn ensure_runtime_mode(app: &AppHandle, state: &DesktopState) -> Result<(), String> {
  let mode = {
    let profile = state.profile.lock().expect("runtime profile lock poisoned");
    profile.mode.clone()
  };

  match mode {
    RuntimeMode::Embedded => {
      let mut backend_guard = state.embedded_backend.lock().expect("embedded backend lock poisoned");
      let needs_spawn = match backend_guard.as_mut() {
        Some(existing) => !embedded_backend_is_alive(existing),
        None => true,
      };
      if needs_spawn {
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
  let mut backend_guard = state.embedded_backend.lock().expect("embedded backend lock poisoned");

  let embedded_running = backend_guard
    .as_mut()
    .is_some_and(embedded_backend_is_alive);
  if !embedded_running {
    *backend_guard = None;
  }
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

#[cfg(test)]
mod tests {
  use super::{command_hint_matches, is_embedded_backend_command, should_create_bootstrap_config};

  #[test]
  fn command_hint_matches_uses_basename() {
    let command_line = "python3 /tmp/project/src/desktop/backend_sidecar.py --host 127.0.0.1 --port 5000";
    assert!(command_hint_matches(command_line, Some("/Users/test/src/desktop/backend_sidecar.py")));
  }

  #[test]
  fn embedded_backend_command_accepts_known_binary() {
    let command_line =
      "/Applications/Oko.app/Contents/Resources/binaries/oko-backend-aarch64-apple-darwin --host 127.0.0.1 --port 8090";
    assert!(is_embedded_backend_command(
      command_line,
      Some("/Applications/Oko.app/Contents/Resources/binaries/oko-backend-aarch64-apple-darwin")
    ));
  }

  #[test]
  fn embedded_backend_command_rejects_missing_flags() {
    let command_line = "python3 /tmp/backend_sidecar.py";
    assert!(!is_embedded_backend_command(command_line, Some("/tmp/backend_sidecar.py")));
  }

  #[test]
  fn embedded_backend_command_rejects_hint_mismatch() {
    let command_line = "python3 /tmp/backend_sidecar.py --host 127.0.0.1 --port 8090";
    assert!(!is_embedded_backend_command(command_line, Some("/tmp/other_script.py")));
  }

  #[test]
  fn bootstrap_config_created_only_for_first_run_without_db() {
    assert!(should_create_bootstrap_config(false, false));
    assert!(!should_create_bootstrap_config(true, false));
    assert!(!should_create_bootstrap_config(false, true));
    assert!(!should_create_bootstrap_config(true, true));
  }
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

  let app = builder
    .build(tauri::generate_context!())
    .unwrap_or_else(|error| panic!("error while building Oko desktop: {error}"));

  app.run(|app_handle, event| {
    if let RunEvent::Exit = event {
      if let Some(state_ref) = app_handle.try_state::<DesktopState>() {
        stop_embedded_backend(state_ref.inner());
      }
    }
  });
}
