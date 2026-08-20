import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is a local-dev convenience only; not required in CI

from src import internships, new_grad


def main() -> int:
    internships_ok = internships.run()
    new_grad_ok = new_grad.run()
    return 0 if (internships_ok and new_grad_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
