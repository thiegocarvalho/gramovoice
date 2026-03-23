import os
import asyncio
import sys
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent
from tts_engine import TTSEngine, AVAILABLE_VOICES
from utils import load_settings, setup_bundle_paths, setup_environment

setup_bundle_paths()
setup_environment()

server = Server("gramovoice")
settings = load_settings()
engine = TTSEngine(
    max_chars=settings.get("max_chars", 300),
    default_language=settings.get("language", "pt-br")
)

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_audio",
            description="Generate a voiceover audio file using GramoVoice engine (PT-BR).",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "project_name": {"type": "string"},
                    "voice": {"type": "string", "default": "Dora (Feminino)", "enum": list(AVAILABLE_VOICES.keys())},
                    "speed": {"type": "number", "default": 1.0},
                    "chunk_size": {"type": "integer", "default": 300}
                },
                "required": ["text", "project_name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Handles execution of registered MCP tools."""
    if name != "generate_audio":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        raise ValueError("Missing arguments")

    text = arguments.get("text")
    project_name = arguments.get("project_name")
    voice = arguments.get("voice", "Dora (Feminino)")
    speed = arguments.get("speed", 1.0)
    chunk_size = arguments.get("chunk_size", 300)

    output_dir = os.path.join(os.getcwd(), "out")
    os.makedirs(output_dir, exist_ok=True)

    basename = os.path.basename(project_name)
    filename = f"{basename}.wav" if not (basename.endswith(".mp3") or basename.endswith(".wav")) else basename
    target_path = os.path.join(output_dir, filename)

    print(f"MCP Tool: Synthesizing {filename}...", file=sys.stderr, flush=True)

    def mcp_progress_cb(p):
        print(f"Progress: {int(p * 100)}%", file=sys.stderr, flush=True)

    engine.max_chars = chunk_size
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(
        None,
        lambda: engine.synthesize(
            text=text,
            output_path=target_path,
            speed=speed,
            speaker_wav=voice,
            progress_callback=mcp_progress_cb
        )
    )

    if success:
        return [TextContent(type="text", text=f"Success! Audio saved to: {target_path}")]
    else:
        return [TextContent(type="text", text="Error: Synthesis failed.")]

async def main() -> None:
    """Main execution loop for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
