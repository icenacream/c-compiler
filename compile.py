#!/usr/bin/env python3
"""
PyCCompiler — A C compiler written in Python
Usage:
    python compile.py <source.c> [options]

Options:
    -o <file>       Output file (default: <source>.py)
    --ir            Also emit IR (intermediate representation)
    --ast           Print the AST
    --tokens        Print the token stream
    --run           Compile and run immediately
    --no-semantic   Skip semantic analysis
    -h, --help      Show this help message
"""

import sys
import os
import argparse
import subprocess
from pycc import (
    Lexer, LexerError,
    Parser, ParseError,
    SemanticAnalyzer, SemanticError,
    IRGen, PythonCodeGen,
    ASTPrinter,
)

BANNER = """
╔═══════════════════════════════════════════════╗
║         PyCCompiler v1.0 — C → Python         ║
║  Phases: Lex → Parse → Semantic → CodeGen     ║
╚═══════════════════════════════════════════════╝
"""

SEPARATOR = "─" * 60


def colored(text, code):
    """ANSI color helper."""
    return f"\033[{code}m{text}\033[0m"

def green(t): return colored(t, "32")
def red(t): return colored(t, "31")
def yellow(t): return colored(t, "33")
def cyan(t): return colored(t, "36")
def bold(t): return colored(t, "1")


def compile_source(source: str, filename: str = "<stdin>",
                   show_tokens=False, show_ast=False, show_ir=False,
                   skip_semantic=False, verbose=True):
    """
    Run all compiler phases and return the generated Python code.
    Returns (python_code, warnings) or raises on error.
    """
    results = {}

    #  Phase 1: Lexing 
    if verbose:
        print(bold(f"\n{'─'*20} Phase 1: Lexical Analysis {'─'*20}"))
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        if verbose:
            print(green(f"  ✓ Tokenized {len(tokens)-1} tokens"))
        results['tokens'] = tokens

        if show_tokens:
            print(f"\n  {'Token':<25} {'Value':<20} {'Line':>6} {'Col':>5}")
            print(f"  {'─'*25} {'─'*20} {'─'*6} {'─'*5}")
            for tok in tokens[:-1]:  # skip EOF
                print(f"  {tok.type.name:<25} {repr(tok.value):<20} {tok.line:>6} {tok.col:>5}")

    except LexerError as e:
        print(red(f"\n  ✗ {e}"))
        raise

    #  Phase 2: Parsing 
    if verbose:
        print(bold(f"\n{'─'*20} Phase 2: Parsing {'─'*28}"))
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        func_count = sum(1 for d in ast.declarations if hasattr(d, 'params'))
        var_count  = sum(1 for d in ast.declarations if not hasattr(d, 'params'))
        if verbose:
            print(green(f"  ✓ AST built — {func_count} function(s), {var_count} global variable(s)"))
        results['ast'] = ast

        if show_ast:
            printer = ASTPrinter()
            print("\n" + printer.print(ast))

    except ParseError as e:
        print(red(f"\n  ✗ {e}"))
        raise

    #  Phase 3: Semantic Analysis 
    if not skip_semantic:
        if verbose:
            print(bold(f"\n{'─'*20} Phase 3: Semantic Analysis {'─'*18}"))
        analyzer = SemanticAnalyzer()
        ok = analyzer.analyze(ast)

        for w in analyzer.warnings:
            print(yellow(f"  ⚠  {w}"))

        if not ok:
            for err in analyzer.errors:
                print(red(f"  ✗ {err}"))
            raise SemanticError(f"{len(analyzer.errors)} semantic error(s) found")

        if verbose:
            print(green(f"  ✓ No semantic errors"))
        results['warnings'] = analyzer.warnings

    #  Phase 4: IR Generation 
    if show_ir:
        if verbose:
            print(bold(f"\n{'─'*20} Phase 4a: IR Generation {'─'*21}"))
        ir_gen = IRGen()
        ir_code = ir_gen.generate(ast)
        print("\n" + ir_code)
        results['ir'] = ir_code

    #  Phase 4: Code Generation 
    if verbose:
        print(bold(f"\n{'─'*20} Phase 4b: Code Generation {'─'*19}"))
    codegen = PythonCodeGen()
    python_code = codegen.generate(ast)
    if verbose:
        lines = python_code.count('\n')
        print(green(f"  ✓ Generated {lines} lines of Python code"))

    results['python'] = python_code
    return results


def main():
    parser = argparse.ArgumentParser(
        description="PyCCompiler — C to Python compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("source", nargs="?", help="C source file to compile")
    parser.add_argument("-o", "--output", help="Output Python file")
    parser.add_argument("--ir", action="store_true", help="Emit IR")
    parser.add_argument("--ast", action="store_true", help="Print AST")
    parser.add_argument("--tokens", action="store_true", help="Print tokens")
    parser.add_argument("--run", action="store_true", help="Compile and run")
    parser.add_argument("--no-semantic", action="store_true", help="Skip semantic analysis")
    parser.add_argument("--demo", action="store_true", help="Run built-in demo")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress compilation output")
    args = parser.parse_args()

    print(BANNER)

    if args.demo or not args.source:
        run_demo(args)
        return

    # Read source file
    if not os.path.exists(args.source):
        print(red(f"Error: File not found: {args.source}"))
        sys.exit(1)

    with open(args.source, 'r') as f:
        source = f.read()

    filename = os.path.basename(args.source)
    print(f"  Compiling: {bold(filename)}")

    try:
        results = compile_source(
            source, filename,
            show_tokens=args.tokens,
            show_ast=args.ast,
            show_ir=args.ir,
            skip_semantic=args.no_semantic,
            verbose=not args.quiet,
        )
    except (LexerError, ParseError, SemanticError) as e:
        print(red(f"\nCompilation failed: {e}"))
        sys.exit(1)

    # Write output
    python_code = results['python']
    outfile = args.output or args.source.replace('.c', '.py').replace('.C', '.py')
    if outfile == args.source:
        outfile = args.source + '.py'

    with open(outfile, 'w') as f:
        f.write(python_code)

    print(f"\n{green('✓')} Compiled to: {bold(outfile)}")

    #  Save to tests/ folder 
    import shutil
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    os.makedirs(tests_dir, exist_ok=True)

    base      = os.path.splitext(os.path.basename(args.source))[0]
    test_c    = os.path.join(tests_dir, os.path.basename(args.source))
    test_py   = os.path.join(tests_dir, base + ".py")

    shutil.copy2(args.source, test_c)
    with open(test_py, 'w') as f:
        f.write(python_code)

    print(f"{green('✓')} Saved to tests/:  {bold(os.path.basename(test_c))}  +  {bold(os.path.basename(test_py))}")
    print(SEPARATOR)

    if args.run:
        print(f"\n{bold('Running program...')}")
        print(SEPARATOR)
        subprocess.run([sys.executable, outfile])


def run_demo(args):
    """Run built-in demo programs."""
    demos = {
        "hello": (
            "Hello World",
            r"""
int main() {
    printf("Hello, World!\n");
    return 0;
}
"""
        ),
        "fibonacci": (
            "Fibonacci Sequence",
            r"""
int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

int main() {
    int i;
    printf("Fibonacci sequence (first 10):\n");
    for (i = 0; i < 10; i++) {
        printf("fib(%d) = %d\n", i, fibonacci(i));
    }
    return 0;
}
"""
        ),
        "bubblesort": (
            "Bubble Sort",
            r"""
int main() {
    int n;
    int i;
    int j;
    int temp;
    n = 8;
    int arr[8];
    arr[0] = 64;
    arr[1] = 34;
    arr[2] = 25;
    arr[3] = 12;
    arr[4] = 22;
    arr[5] = 11;
    arr[6] = 90;
    arr[7] = 47;

    printf("Before sorting: ");
    for (i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");

    for (i = 0; i < n - 1; i++) {
        for (j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }

    printf("After sorting:  ");
    for (i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
    return 0;
}
"""
        ),
        "factorial": (
            "Factorial (iterative + recursive)",
            r"""
int factorial_iter(int n) {
    int result;
    result = 1;
    int i;
    for (i = 1; i <= n; i++) {
        result = result * i;
    }
    return result;
}

int factorial_rec(int n) {
    if (n <= 1) return 1;
    return n * factorial_rec(n - 1);
}

int main() {
    int i;
    printf("Factorials (iterative vs recursive):\n");
    for (i = 0; i <= 10; i++) {
        printf("  %d! = %d (iter) = %d (rec)\n",
               i, factorial_iter(i), factorial_rec(i));
    }
    return 0;
}
"""
        ),
        "fizzbuzz": (
            "FizzBuzz",
            r"""
int main() {
    int i;
    for (i = 1; i <= 30; i++) {
        if (i % 15 == 0) {
            printf("FizzBuzz\n");
        } else if (i % 3 == 0) {
            printf("Fizz\n");
        } else if (i % 5 == 0) {
            printf("Buzz\n");
        } else {
            printf("%d\n", i);
        }
    }
    return 0;
}
"""
        ),
    }

    print(f"  {bold('Built-in Demo Programs:')}")
    for key, (name, _) in demos.items():
        print(f"    {cyan(key):<20} {name}")
    print()

    demo_key = input("  Enter demo name (or 'all'): ").strip().lower()

    to_run = list(demos.items()) if demo_key == 'all' else [(demo_key, demos[demo_key])] if demo_key in demos else []

    if not to_run:
        print(red("  Unknown demo. Exiting."))
        return

    for key, (name, source) in to_run:
        print(f"\n{SEPARATOR}")
        print(bold(f"Demo: {name}"))
        print(SEPARATOR)

        try:
            results = compile_source(
                source, f"{key}.c",
                show_tokens=args.tokens,
                show_ast=args.ast,
                show_ir=args.ir,
                verbose=not args.quiet,
            )
        except Exception as e:
            print(red(f"Compilation failed: {e}"))
            continue

        # Write and run
        import tempfile
        outfile = os.path.join(tempfile.gettempdir(), f"demo_{key}.py")
        with open(outfile, 'w') as f:
            f.write(results['python'])

        print(f"\n{bold('Output:')}")
        print(SEPARATOR)
        subprocess.run([sys.executable, outfile])
        print(SEPARATOR)


if __name__ == "__main__":
    main()