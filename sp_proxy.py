"""
Super Productivity API Proxy

Runs on the same machine as Super Productivity and exposes the
Local REST API (127.0.0.1:3876) to the local network so that
Home Assistant on another machine can reach it.

Usage:
    python sp_proxy.py

This listens on 0.0.0.0:3877 and forwards to 127.0.0.1:3876,
rewriting the Host header so Super Productivity accepts the request.

To run as a background task on Windows startup:
    1. Win+R > shell:startup
    2. Create a shortcut to: pythonw sp_proxy.py
"""

import asyncio
import sys

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 3877
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 3876


async def handle_client(reader, writer):
    """Handle a single client connection."""
    try:
        # Read the full HTTP request
        request_data = b""
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=10)
            if not line:
                break
            # Rewrite the Host header
            if line.lower().startswith(b"host:"):
                line = f"Host: {TARGET_HOST}:{TARGET_PORT}\r\n".encode()
            request_data += line
            if line == b"\r\n":
                break

        # Check for Content-Length to read body
        content_length = 0
        for header_line in request_data.split(b"\r\n"):
            if header_line.lower().startswith(b"content-length:"):
                content_length = int(header_line.split(b":")[1].strip())
                break

        if content_length > 0:
            body = await asyncio.wait_for(
                reader.readexactly(content_length), timeout=10
            )
            request_data += body

        # Connect to Super Productivity
        target_reader, target_writer = await asyncio.open_connection(
            TARGET_HOST, TARGET_PORT
        )

        # Forward the request
        target_writer.write(request_data)
        await target_writer.drain()

        # Read and forward the response
        response = b""
        while True:
            chunk = await asyncio.wait_for(target_reader.read(4096), timeout=15)
            if not chunk:
                break
            response += chunk

        writer.write(response)
        await writer.drain()

        target_writer.close()
        await target_writer.wait_closed()

    except Exception:
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    """Start the proxy server."""
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    addr = server.sockets[0].getsockname()
    print(f"SP API Proxy listening on {addr[0]}:{addr[1]}")
    print(f"Forwarding to {TARGET_HOST}:{TARGET_PORT}")
    print(f"Configure HA integration with host: <this PC's LAN IP>, port: {LISTEN_PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProxy stopped.")
        sys.exit(0)
