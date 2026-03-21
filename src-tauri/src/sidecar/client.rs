use serde::{de::DeserializeOwned, Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

#[derive(Debug, Serialize)]
struct JsonRpcRequest<P: Serialize> {
    jsonrpc: &'static str,
    id: u64,
    method: String,
    params: P,
}

#[derive(Debug, Deserialize)]
struct JsonRpcResponse {
    #[allow(dead_code)]
    jsonrpc: String,
    #[allow(dead_code)]
    id: Option<u64>,
    result: Option<serde_json::Value>,
    error: Option<JsonRpcError>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    pub data: Option<serde_json::Value>,
}

impl std::fmt::Display for JsonRpcError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "JSON-RPC error {}: {}", self.code, self.message)
    }
}

/// The sidecar client manages the Python subprocess lifecycle and JSON-RPC communication.
pub struct SidecarClient {
    process: Mutex<Option<Child>>,
    stdin: Mutex<Option<std::process::ChildStdin>>,
    stdout: Mutex<Option<BufReader<std::process::ChildStdout>>>,
    next_id: AtomicU64,
}

/// Spawn a background thread that reads lines from the sidecar's stderr and
/// forwards them to the Tauri log so they appear in the developer console.
fn forward_stderr(stderr: std::process::ChildStderr) {
    use std::io::BufRead;
    std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            match line {
                Ok(l) => log::debug!("[sidecar] {l}"),
                Err(_) => break,
            }
        }
    });
}

impl SidecarClient {
    pub fn new() -> Self {
        Self {
            process: Mutex::new(None),
            stdin: Mutex::new(None),
            stdout: Mutex::new(None),
            next_id: AtomicU64::new(1),
        }
    }

    /// Spawn the Python sidecar process.
    pub fn spawn(&self, python_path: &str, project_dir: &str) -> Result<(), String> {
        let child = Command::new(python_path)
            .args(["-m", "kindleocr"])
            .current_dir(project_dir)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

        let mut child = child;
        let stdin = child.stdin.take().ok_or("Failed to capture sidecar stdin")?;
        let stdout = child.stdout.take().ok_or("Failed to capture sidecar stdout")?;
        let stderr = child.stderr.take().ok_or("Failed to capture sidecar stderr")?;
        forward_stderr(stderr);

        *self.process.lock().map_err(|e| e.to_string())? = Some(child);
        *self.stdin.lock().map_err(|e| e.to_string())? = Some(stdin);
        *self.stdout.lock().map_err(|e| e.to_string())? = Some(BufReader::new(stdout));

        Ok(())
    }

    /// Send a JSON-RPC call and wait for the response.
    pub fn call<P: Serialize, R: DeserializeOwned>(
        &self,
        method: &str,
        params: P,
    ) -> Result<R, String> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);

        let request = JsonRpcRequest {
            jsonrpc: "2.0",
            id,
            method: method.to_string(),
            params,
        };

        let mut request_line =
            serde_json::to_string(&request).map_err(|e| format!("Serialize error: {e}"))?;
        request_line.push('\n');

        // Write request
        {
            let mut stdin_guard = self.stdin.lock().map_err(|e| e.to_string())?;
            let stdin = stdin_guard
                .as_mut()
                .ok_or("Sidecar not running")?;
            stdin
                .write_all(request_line.as_bytes())
                .map_err(|e| format!("Failed to write to sidecar: {e}"))?;
            stdin
                .flush()
                .map_err(|e| format!("Failed to flush sidecar stdin: {e}"))?;
        }

        // Read response
        let response_line = {
            let mut stdout_guard = self.stdout.lock().map_err(|e| e.to_string())?;
            let stdout = stdout_guard
                .as_mut()
                .ok_or("Sidecar not running")?;
            let mut line = String::new();
            stdout
                .read_line(&mut line)
                .map_err(|e| format!("Failed to read from sidecar: {e}"))?;
            line
        };

        if response_line.trim().is_empty() {
            return Err("Sidecar returned empty response (process may have exited)".to_string());
        }

        let response: JsonRpcResponse = serde_json::from_str(response_line.trim())
            .map_err(|e| format!("Failed to parse sidecar response: {e}"))?;

        if let Some(error) = response.error {
            return Err(error.to_string());
        }

        let result_value = response.result.ok_or("Missing result in response")?;
        serde_json::from_value(result_value).map_err(|e| format!("Failed to deserialize result: {e}"))
    }

    /// Check if the sidecar is running.
    pub fn is_running(&self) -> bool {
        let Ok(guard) = self.process.lock() else {
            return false;
        };
        guard.is_some()
    }

    /// Shut down the sidecar by closing stdin and waiting for exit.
    pub fn shutdown(&self) -> Result<(), String> {
        // Drop stdin to signal EOF
        {
            let mut stdin_guard = self.stdin.lock().map_err(|e| e.to_string())?;
            *stdin_guard = None;
        }

        // Wait for process to exit
        let mut proc_guard = self.process.lock().map_err(|e| e.to_string())?;
        if let Some(mut child) = proc_guard.take() {
            let _ = child.wait();
        }

        // Clean up stdout
        let mut stdout_guard = self.stdout.lock().map_err(|e| e.to_string())?;
        *stdout_guard = None;

        Ok(())
    }
}

impl Drop for SidecarClient {
    fn drop(&mut self) {
        let _ = self.shutdown();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn python_path() -> String {
        // Use the venv Python if available
        let venv = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .join("src-python")
            .join(".venv")
            .join("Scripts")
            .join("python.exe");
        if venv.exists() {
            venv.to_string_lossy().to_string()
        } else {
            "python".to_string()
        }
    }

    fn project_dir() -> String {
        let mut p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        p.pop();
        p.join("src-python").to_string_lossy().to_string()
    }

    #[test]
    fn spawn_and_ping() {
        let client = SidecarClient::new();
        client.spawn(&python_path(), &project_dir()).expect("spawn failed");
        assert!(client.is_running());

        let result: Value = client.call("ping", serde_json::json!({})).expect("ping failed");
        assert_eq!(result["status"], "ok");
        assert!(result["version"].is_string());

        client.shutdown().expect("shutdown failed");
    }

    #[test]
    fn graceful_shutdown() {
        let client = SidecarClient::new();
        client.spawn(&python_path(), &project_dir()).expect("spawn failed");
        client.shutdown().expect("shutdown failed");
        assert!(!client.is_running());
    }

    #[test]
    fn method_not_found() {
        let client = SidecarClient::new();
        client.spawn(&python_path(), &project_dir()).expect("spawn failed");

        let result: Result<Value, String> = client.call("nonexistent", serde_json::json!({}));
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("-32601"));

        client.shutdown().expect("shutdown failed");
    }
}
