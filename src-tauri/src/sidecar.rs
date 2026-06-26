use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};

pub struct Sidecar {
    child: Child,
}

impl Sidecar {
    /// Spawne `python <script> --sidecar`. stdin/stdout sont des pipes.
    /// stderr est hérité (les logs Python restent visibles dans le terminal).
    pub fn spawn(python: &str, script: &str) -> Result<Self, String> {
        let child = Command::new(python)
            .args([script, "--sidecar"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|e| format!("sidecar spawn failed: {e}"))?;
        Ok(Self { child })
    }

    /// Envoie une commande JSON sur stdin du sidecar.
    pub fn send_cmd(&mut self, cmd: &str) -> Result<(), String> {
        let stdin = self.child.stdin.as_mut().ok_or("no stdin handle")?;
        writeln!(stdin, r#"{{"cmd":"{cmd}"}}"#).map_err(|e| e.to_string())
    }

    /// Prend le handle stdout pour le lire dans un thread séparé.
    /// Ne peut être appelé qu'une seule fois (Option → None après).
    pub fn take_stdout(&mut self) -> Option<BufReader<std::process::ChildStdout>> {
        self.child.stdout.take().map(BufReader::new)
    }

    pub fn kill(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Drop for Sidecar {
    fn drop(&mut self) {
        self.kill();
    }
}
