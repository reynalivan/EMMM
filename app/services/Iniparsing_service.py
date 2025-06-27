# app/services/ini_parsing_service.py
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import configparser
import re
import uuid
import shutil
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.logger_utils import logger


@dataclass
class Assignment:
    """Represents a single variable assignment within a keybinding, e.g., '$dress = 0,1,2'."""

    variable: str
    cycle_options: List[str]
    current_value: str  # The actual current value from [Constants]


@dataclass
class KeyBinding:
    """
    A robust, mutable data class to hold all possible information
    from a 3DMigoto [Key...] or [Preset...] section.
    """

    # --- Source & Identity ---
    source_file: Path
    section_name: str
    binding_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- Triggering ---
    keys: List[str] = field(default_factory=list)
    backs: List[str] = field(default_factory=list)

    # --- Behavior ---
    type: str | None = None
    condition: str | None = None
    namespace: Optional[str] = None
    run: str | None = None
    wrap: bool = True

    # --- Variable Assignments ---
    # A dictionary to hold all variable assignments, e.g., {'$swapvar': ['0','1'], 'convergence': ['1.45']}
    assignments: List[Assignment] = field(default_factory=list)


class IniKeyParsingService:
    """
    Parses, modifies, and writes 3DMigoto .ini files, specifically for keybindings.
    This version is significantly improved to handle 3DMigoto's script-like syntax.
    """

    RESERVED_PROPERTIES = {
        "key",
        "back",
        "type",
        "condition",
        "run",
        "wrap",
        "smart",
        "delay",
        "transition",
        "transition_type",
        "release_delay",
        "release_transition",
        "release_transition_type",
    }
    VAR_REGEX = re.compile(r".*(\$\w+)")
    _cache: dict[Path, tuple[float, list[KeyBinding]]] = {}  # {folder: (mtime, data)}

    async def load_keybindings_async(self, folder_path: Path) -> dict:
        """
        Non-blocking load:
        • pakai cache berdasarkan newest mtime di folder.
        • scanning + parsing di thread-pool.
        • hasil sudah urut root-first (lihat _get_ini_files).
        """
        loop = asyncio.get_running_loop()

        # --- cache check --------------------------------------------------
        newest_mtime = max(
            (p.stat().st_mtime for p in folder_path.rglob("*.ini")), default=0.0
        )
        cached = self._cache.get(folder_path)
        if cached and cached[0] >= newest_mtime:
            return {"success": True, "data": cached[1]}

        # --- scan files (stage-1 fn) --------------------------------------
        ini_files = await self.get_ini_files_async(folder_path, depth=4)
        if not ini_files:
            return {"success": True, "data": []}

        # --- parse concurrently ------------------------------------------
        def _parse(path: Path) -> list[KeyBinding]:
            return self._parse_single_ini(path)

        bindings: list[KeyBinding] = []
        with ThreadPoolExecutor() as ex:
            tasks = [loop.run_in_executor(ex, _parse, p) for p in ini_files]
            for coro in asyncio.as_completed(tasks):
                try:
                    bindings.extend(await coro)
                except Exception as e:
                    logger.error("Parsing failed: %s", e, exc_info=True)

        # --- store cache & return ----------------------------------------
        self._cache[folder_path] = (newest_mtime, bindings)
        return {"success": True, "data": bindings}

    # ---------- file discovery (depth-limited, ordered) ----------
    def _scan_ini_files_sync(self, root: Path, max_depth: int = 4) -> List[Path]:
        """Return *.ini paths ≤ max_depth, ordered:
        1) root-level first,
        2) non-'disabled*' before disabled,
        3) alphabetical."""

        def is_disabled(p: Path) -> bool:
            return p.stem.lower().startswith("disabled")

        ini_files: list[Path] = [
            p
            for p in root.rglob("*.ini")
            if len(p.relative_to(root).parts) <= max_depth
        ]

        ini_files.sort(
            key=lambda p: (
                len(p.relative_to(root).parts),  # depth: 0 = root
                is_disabled(p),  # False < True
                str(p).lower(),  # stable alpha
            )
        )
        return ini_files

    async def get_ini_files_async(
        self, folder_path: Path, depth: int = 4
    ) -> List[Path]:
        """Async wrapper – non-blocking scan."""
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._scan_ini_files_sync, folder_path, depth
        )

    # backward-compatible sync alias for existing codebase
    def _get_ini_files(self, folder_path: Path) -> List[Path]:
        return self._scan_ini_files_sync(folder_path, 4)

    def _parse_single_ini(self, file_path: Path) -> list[KeyBinding]:
        """
        Baca file sekali → hasilkan list KeyBinding.
        - Menangani baris '$var = …' sebelum header sbg local constants
        - `[Constants]` section ikut menambah constants local
        - Dedup key/back, skip $creditinfo
        """
        keybindings: list[KeyBinding] = []
        local_constants: dict[str, str] = {}

        # -------- pass: scan lines, split section & constants ---------------
        sections: dict[str, list[str]] = {}
        cur_name: str | None = None
        cur_lines: list[str] = []

        var_line = re.compile(r"\s*\$(\w+)\s*=\s*(.*)")
        for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines(
            keepends=True
        ):
            stripped = line.strip()

            # header
            if stripped.startswith("[") and stripped.endswith("]"):
                if cur_name is not None:
                    sections[cur_name] = cur_lines
                cur_name, cur_lines = stripped[1:-1], [line]
                continue

            # collect constants when not inside section
            if cur_name is None:
                m = var_line.match(stripped)
                if m:
                    local_constants[m.group(1)] = m.group(2)
                continue

            # inside section
            cur_lines.append(line)

        if cur_name:
            sections[cur_name] = cur_lines

        # -------- parse Constants section (if any) --------------------------
        if "Constants" in sections:
            parser = self._get_configured_parser()
            parser.read_string("".join(sections["Constants"]))
            for k, v in parser.items("Constants"):
                m = self.VAR_REGEX.match(k)
                local_constants[m.group(1) if m else k] = v or ""

        # -------- iterate Key sections --------------------------------------
        for sec_name, lines in sections.items():
            if not sec_name.lower().startswith("key"):
                continue

            parser = self._get_configured_parser()
            parser.read_string("".join(lines))
            data = parser[sec_name]

            # wajib ada 'key'
            if not any(k.lower() == "key" for k in data):
                continue

            # ── keys / backs (split oleh spasi/koma & dedup) ----------------
            def _split_vals(raw: str) -> list[str]:
                """Pisah hanya dengan koma, pertahankan spasi internal."""
                parts = [p.strip() for p in raw.split(",") if p.strip()]
                # dedup sambil mempertahankan urutan
                return list(dict.fromkeys(parts))

            keys = _split_vals(data.get("key", "")) if "key" in data else []
            backs = _split_vals(data.get("back", "")) if "back" in data else []

            # ── assignments --------------------------------------------------
            assigns: list[Assignment] = []
            seen_var: set[str] = set()
            for k, v in data.items():
                if k.lower() in self.RESERVED_PROPERTIES or k.lower() == "$creditinfo":
                    continue
                m = self.VAR_REGEX.match(k)
                if not m:
                    continue
                var = m.group(1)
                if var in seen_var:
                    continue
                seen_var.add(var)
                opts = list(dict.fromkeys(o.strip() for o in v.split(",") if o.strip()))
                cur_val = local_constants.get(var, opts[0] if opts else "")
                assigns.append(
                    Assignment(
                        variable=var,
                        cycle_options=opts,
                        current_value=cur_val,
                    )
                )

            keybindings.append(
                KeyBinding(
                    source_file=file_path,
                    section_name=sec_name,
                    keys=keys,
                    backs=backs,
                    type=data.get("type"),
                    condition=data.get("condition"),
                    run=data.get("run"),
                    wrap=data.getboolean("wrap", fallback=True),
                    assignments=assigns,
                )
            )

        return keybindings

    # ---------------------------------------------------------------------------
    #  Public API  ── parse semua .ini di folder  (thread-pool, depth ≤4)
    # ---------------------------------------------------------------------------
    def parse_ini_files_in_folder(self, folder_path: Path) -> dict:
        """
        Async-friendly parser:
        • gunakan thread-pool → tidak block UI
        • file urut sudah dihasilkan _get_ini_files (root-first, non-disabled dulu)
        • tiap file di-parse sekali ( _parse_single_ini )
        """
        ini_files = self._get_ini_files(folder_path)
        if not ini_files:
            return {"success": True, "data": []}

        from concurrent.futures import ThreadPoolExecutor, as_completed

        all_bindings: list[KeyBinding] = []
        with ThreadPoolExecutor() as ex:
            futures = {ex.submit(self._parse_single_ini, p): p for p in ini_files}
            for fut in as_completed(futures):
                try:
                    all_bindings.extend(fut.result())
                except Exception as e:
                    logger.error(
                        f"Failed parsing {futures[fut].name}: {e}", exc_info=True
                    )

        logger.info(
            "Parsed %d keybindings from %d ini files", len(all_bindings), len(ini_files)
        )
        return {"success": True, "data": all_bindings}

    def _get_configured_parser(self) -> configparser.ConfigParser:
        """Helper to create a pre-configured parser for 3DMigoto .ini files."""
        # strict=False allows duplicate keys, which is essential for 3DMigoto command lists.
        # We will filter sections anyway, but this makes the parser more robust.
        parser = configparser.ConfigParser(
            interpolation=None,
            allow_no_value=True,
            delimiters=("="),
            comment_prefixes=("#", ";"),
            strict=False,
        )
        parser.optionxform = lambda optionstr: optionstr
        return parser

    def _extract_sections_from_file(self, file_path: Path) -> Dict[str, str]:
        """
        Manually reads an .ini file and splits it into a dictionary of sections.
        This avoids file-level parsing errors from configparser.
        """
        sections = {}
        current_section_name = None
        current_section_lines = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line.startswith("[") and stripped_line.endswith("]"):
                        # If we were in a section, save it before starting a new one
                        if current_section_name:
                            sections[current_section_name] = "".join(
                                current_section_lines
                            )

                        # Start the new section
                        current_section_name = stripped_line[1:-1]
                        current_section_lines = [line]
                    elif current_section_name:
                        current_section_lines.append(line)

            # Save the last section in the file
            if current_section_name:
                sections[current_section_name] = "".join(current_section_lines)

        except Exception as e:
            logger.error(
                f"Error reading or splitting file into sections: {file_path.name}: {e}"
            )

        return sections

    def _build_section_string(self, binding: KeyBinding) -> str:
        """Helper to reconstruct a [Key...] section from a KeyBinding object."""
        lines = [f"[{binding.section_name}]\n"]

        # --- Behavior Properties ---
        if binding.condition:
            lines.append(f"condition = {binding.condition}\n")
        if binding.type:
            lines.append(f"type = {binding.type}\n")
        if binding.run:
            lines.append(f"run = {binding.run}\n")

        # Add 'wrap' only if it's set to False (since default is True)
        if binding.wrap is False:
            lines.append("wrap = false\n")

        # --- Trigger Keys ---
        for key in binding.keys:
            lines.append(f"key = {key}\n")
        for back in binding.backs:
            lines.append(f"back = {back}\n")

        # --- Variable Assignments ---
        for assignment in binding.assignments:
            # Get the value to write. If it's a cycle, join. If not, use current_value.
            # This assumes current_value reflects the desired state to be saved.
            value_to_write = ",".join(assignment.cycle_options)
            lines.append(f"{assignment.variable} = {value_to_write}\n")

        return "".join(lines)

    def save_ini_changes(self, modified_bindings: List[KeyBinding]) -> dict:
        """
        Flow 5.2 Part D: Saves keybinding changes back to their respective source .ini files.
        Uses a read-modify-write approach to preserve the original file structure.
        """
        # 1. Group modified bindings by their source file
        changes_by_file: Dict[Path, List[KeyBinding]] = defaultdict(list)
        for binding in modified_bindings:
            changes_by_file[binding.source_file].append(binding)

        errors = []

        for file_path, bindings in changes_by_file.items():
            try:
                # 2. Create a one-time backup if it doesn't exist
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                if not backup_path.exists():
                    shutil.copy2(file_path, backup_path)
                    logger.info(
                        f"Created backup for '{file_path.name}' at '{backup_path.name}'"
                    )

                # 3. Read all lines from the original file
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    original_lines = f.readlines()

                # Create a lookup map for faster access
                modified_sections = {b.section_name: b for b in bindings}

                new_lines = []
                in_section_to_replace = False

                # 4. Atomically Read, Modify, and Write back the content
                for line in original_lines:
                    stripped_line = line.strip()

                    if stripped_line.startswith("[") and stripped_line.endswith("]"):
                        # This line is a section header
                        current_section_name = stripped_line[1:-1]

                        if current_section_name in modified_sections:
                            # If this is a section we need to replace, flag it,
                            # write the new content, and prepare to skip old lines.
                            in_section_to_replace = True
                            binding_to_write = modified_sections[current_section_name]
                            new_section_content = self._build_section_string(
                                binding_to_write
                            )
                            new_lines.append(new_section_content)
                        else:
                            # If it's a different section, turn off the flag and keep the line.
                            in_section_to_replace = False
                            new_lines.append(line)
                    else:
                        # If this line is NOT a section header
                        if not in_section_to_replace:
                            # Keep the line if we are not inside a section that needs replacing
                            new_lines.append(line)
                        # If we ARE inside a section to replace, do nothing (skip the old line)

                # 5. Write the modified content back to the original file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                logger.info(
                    f"Successfully saved {len(bindings)} changes to '{file_path.name}'"
                )

            except Exception as e:
                error_msg = f"Failed to save changes to '{file_path.name}': {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        return {"success": not errors, "errors": errors}
