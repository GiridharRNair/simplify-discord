import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is a local-dev convenience only; not required in CI

from src import internships, new_grad


def main() -> int:
    results = [
        internships.run(),
        new_grad.run(),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
