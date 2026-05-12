# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/services/ssh.py
#
# Thin async wrapper around Paramiko for SSH command execution and SFTP writes.
#
# Because Paramiko is synchronous, all blocking calls are run in a thread-pool
# executor via asyncio.get_event_loop().run_in_executor(None, ...) so they
# don't block the FastAPI event loop.
#
# Functions:
#   ssh_run(server, command) → str
#     Connects, runs command with a 120s timeout, returns stdout.
#     Raises RuntimeError if the exit code is non-zero (stderr included).
#
#   ssh_write_file(server, remote_path, content) → None
#     Opens an SFTP channel and writes the string to the given remote path.
#     Used by routers/lbalancer.py to push the Traefik YAML config.
#
# Connection:
#   _make_client() builds a Paramiko SSHClient authenticating with the RSA
#   private key stored in Server.ssh_private_key (PEM string, not a file path).
#   AutoAddPolicy accepts any host key — acceptable for internal servers;
#   pin known_hosts in production if needed.
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
import io

import paramiko

from models import Server


def _make_client(server: Server) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    pkey = paramiko.RSAKey.from_private_key(io.StringIO(server.ssh_private_key))
    client.connect(
        hostname=server.hostname,
        port=server.ssh_port,
        username=server.ssh_user,
        pkey=pkey,
        timeout=15,
    )
    return client


async def ssh_run(server: Server, command: str) -> str:
    """Run a shell command over SSH and return stdout. Raises on non-zero exit."""
    def _run():
        client = _make_client(server)
        try:
            stdin, stdout, stderr = client.exec_command(command, timeout=120)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode()
            err = stderr.read().decode()
            if exit_code != 0:
                raise RuntimeError(f"Command failed (exit {exit_code}):\n{err or out}")
            return out
        finally:
            client.close()

    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def ssh_write_file(server: Server, remote_path: str, content: str) -> None:
    """Write a string to a remote file via SFTP."""
    def _write():
        client = _make_client(server)
        try:
            sftp = client.open_sftp()
            with sftp.file(remote_path, "w") as f:
                f.write(content)
            sftp.close()
        finally:
            client.close()

    await asyncio.get_event_loop().run_in_executor(None, _write)
