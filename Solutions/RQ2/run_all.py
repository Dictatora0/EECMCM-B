from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load_module(filename: str):
    path = SCRIPT_DIR / filename
    spec = spec_from_file_location(path.stem.replace(".", "_"), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    for filename in ["2_1.py"]:
        module = load_module(filename)
        module.main()


if __name__ == "__main__":
    main()
