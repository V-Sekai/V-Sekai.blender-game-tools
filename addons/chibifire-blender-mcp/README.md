# chibifire-blender-mcp

A Blender addon plus MCP server that lets Claude (and other MCP clients) drive Blender for prompt-assisted modeling, scene construction, and asset import.

Fork of [BlenderMCP](https://github.com/ahujasid/blender-mcp) by Siddharth Ahuja. Maintained by K. S. Ernest (iFire) Lee.

## Features

- TCP socket server inside Blender; JSON command protocol on port 9876 (configurable)
- Auto-connects on Blender launch (toggle in addon preferences)
- Create, modify, delete objects; apply materials; inspect scene and per-object data
- Run arbitrary Python inside Blender from the client
- Capture viewport screenshots
- Optional asset integrations: Poly Haven, Sketchfab, Hyper3D Rodin, Tencent Hunyuan 3D
- No telemetry. The addon makes no outbound HTTP requests unless you opt into an asset integration

## Architecture

- `src/blender_mcp_addon/` — Blender addon (Extension format with `blender_manifest.toml`). Hosts the TCP server and dispatches commands.
  - `__init__.py` — registration entry point
  - `server.py` — `BlenderMCPServer` core (socket, dispatch, scene/object/screenshot, `execute_code`)
  - `preferences.py`, `panel.py`, `operators.py`, `state.py`, `common.py`
  - `integrations/{polyhaven,sketchfab,hyper3d,hunyuan3d}.py` — per-service mixins
- `src/blender_mcp/server.py` — FastMCP server. Connects to the addon socket and exposes Blender as MCP tools.

Settings (port, integration toggles, API keys) live in the addon's user preferences, so they survive File > New, Open File, and scene resets.

## Install

### Prerequisites

- Blender 4.2+ (recommended; uses the Extensions system)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

On macOS:
```bash
brew install uv
```
On Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Blender addon

#### 1. Build the addon zip

Clone this repo, then zip the package directory:

macOS / Linux:
```bash
git clone https://github.com/chibifire/chibifire-blender-mcp
cd chibifire-blender-mcp/src
zip -r ../blender_mcp_addon.zip blender_mcp_addon
```

Windows (PowerShell):
```powershell
git clone https://github.com/chibifire/chibifire-blender-mcp
cd chibifire-blender-mcp\src
Compress-Archive -Path blender_mcp_addon -DestinationPath ..\blender_mcp_addon.zip
```

The result is `blender_mcp_addon.zip` at the repo root.

#### 2. Install in Blender

**Blender 4.2+ (Extensions system, recommended):**

Drag `blender_mcp_addon.zip` onto a Blender window and confirm the install prompt.

Or, via menu: **Edit > Preferences > Get Extensions**, click the **▼** dropdown in the top-right of the panel, choose **Install from Disk...**, and pick the zip. Search for *Blender MCP* and enable it.

**Blender 3.0–4.1 (legacy add-on system):**

**Edit > Preferences > Add-ons**, click **Install...**, pick the zip, then tick the checkbox next to **Interface: Blender MCP**.

#### 3. Configure

Open **Edit > Preferences > Add-ons > Blender MCP** for full settings, or use the 3D Viewport sidebar (press `N`) under the **BlenderMCP** tab for the most common toggles. The server auto-starts on launch by default; uncheck **Auto-connect on Blender launch** to opt out.

#### Updating

To upgrade, repeat steps 1–2 with a fresh clone (or `git pull` and re-zip). Blender replaces the existing install. Your preferences (port, integration toggles, API keys) are stored per-user and survive reinstalls.

#### Uninstall

In the same Add-ons / Get Extensions panel, expand the entry and click **Remove** (or **Uninstall**).

### MCP client config

Point your client at this fork via `uvx --from git+...`. The console script is still `blender-mcp`.

#### Claude Desktop

In `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "blender": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/chibifire/chibifire-blender-mcp",
                "blender-mcp"
            ]
        }
    }
}
```

#### Claude Code

```bash
claude mcp add blender -- uvx --from git+https://github.com/chibifire/chibifire-blender-mcp blender-mcp
```

#### Cursor

Same JSON as Claude Desktop. Use the global MCP setting, or create `.cursor/mcp.json` in your project root.

On Windows, wrap the command in `cmd /c`:

```json
{
    "mcpServers": {
        "blender": {
            "command": "cmd",
            "args": [
                "/c",
                "uvx",
                "--from",
                "git+https://github.com/chibifire/chibifire-blender-mcp",
                "blender-mcp"
            ]
        }
    }
}
```

Run only one MCP server at a time. If both Cursor and Claude Desktop launch one, they will fight over the Blender socket.

### Environment variables

- `BLENDER_HOST` (default `localhost`)
- `BLENDER_PORT` (default `9876`)

## Use

![BlenderMCP in the sidebar](assets/addon-instructions.png)

1. Enable the addon. The MCP server starts automatically on the configured port (default 9876). To opt out of autostart, uncheck **Auto-connect on Blender launch** in the addon preferences.
2. In the 3D View sidebar (`N`) under **BlenderMCP**, toggle whichever asset integrations you want.
3. Start your MCP client. Tools appear under the hammer icon.

To stop or restart the server manually, use the **Disconnect from MCP server** / **Connect to MCP server** button in the BlenderMCP panel.

![BlenderMCP in the sidebar](assets/hammer-icon.png)

### What you can ask Claude to do

- "Create a low-poly dungeon scene with a dragon guarding gold"
- "Build a beach scene using Poly Haven HDRIs, rocks, and vegetation"
- "Make this car red and metallic"
- "Generate a garden gnome through Hyper3D"
- "Get the current scene info and render it as a three.js sketch"
- "Point the camera at the scene and make it isometric"

## Hyper3D

A free-trial key is bundled and limits generations per day. For higher limits, get your own key from hyper3d.ai or fal.ai and paste it into the Hyper3D API Key field.

## Troubleshooting

- **No connection.** Confirm the panel reads "Disconnect from MCP server" (server is up). If it reads "Connect", autostart was disabled or the previous start failed — click it. Confirm your MCP client is configured. Do not run `uvx ... blender-mcp` manually in a terminal; the client launches it.
- **Timeouts.** Break the request into smaller steps.
- **Poly Haven flakiness.** Claude is sometimes erratic about choosing assets; restate the request.
- **Persistent failures.** Restart Blender and the MCP client.

## Protocol

JSON over TCP. Each command is a JSON object with `type` and optional `params`. Each response has `status` plus either `result` or `message`.

## Caveats

- `execute_blender_code` runs arbitrary Python in Blender. Save your work first.
- Poly Haven downloads assets to disk; disable it in the panel if you don't want that.
- Complex operations may need to be broken into smaller steps.

## License

MIT. See `LICENSE`.
