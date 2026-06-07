import subprocess
import sys
import os

if len(sys.argv) != 3:
    print("Usage: run_default.py <input_directory> <output_directory>")
    print("Compiles the default set of data and outputs it to the given output directory")
    sys.exit(1)

indir = sys.argv[1]
outdir = sys.argv[2]
#
# argsets = [
#     [os.path.join(outdir, "Single"), "-S"],
#     [os.path.join(outdir, "Batch10"), "-B", "-F", "(10)"],
#     [os.path.join(outdir, "Batch100"), "-B", "-F", "(100)"],
#     [os.path.join(outdir, "Batch1000"), "-B", "-F", "(1000)"],
#     [os.path.join(outdir, "QAC_SingleBatchComp_Unbounded"), "-c", "-F", "QAC", "-F", "Bounded"],
#     [os.path.join(outdir, "QAC_SingleBatchComp_Bounded"), "-c", "-F", "QAC", "-f", "Bounded"],
#     [os.path.join(outdir, "Single_Comps"), "-S", "-F", "QAC", "-F", "char", "-H", "moodycamel [With Tokens] (char, size 65536)"],
#     [os.path.join(outdir, "Single_Comps"), "-S", "-F", "QAC", "-F", "int64_t", "-H", "moodycamel [With Tokens] (int64_t, size 65536)"],
#     [os.path.join(outdir, "Single_Comps"), "-S", "-F", "QAC", "-F", "FixedStaticString64", "-H", "moodycamel [With Tokens] (FixedStaticString64, size 65536)"],
#     [os.path.join(outdir, "Single_Comps"), "-S", "-F", "QAC", "-F", "char", "-H", "ramalhete_queue [Preallocated] (char)"],
#     [os.path.join(outdir, "Single_Comps"), "-S", "-F", "QAC", "-F", "int64_t", "-H", "ramalhete_queue [Preallocated] (int64_t)"],
#     [os.path.join(outdir, "Single_Comps"), "-S", "-F", "QAC", "-F", "FixedStaticString64", "-H", "ramalhete_queue [Preallocated] (FixedStaticString64)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(10)", "-F", "char", "-H", "moodycamel [Batch With Tokens (10)] (char, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(10)", "-F", "int64_t", "-H", "moodycamel [Batch With Tokens (10)] (int64_t, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(10)", "-F", "FixedStaticString64", "-H", "moodycamel [Batch With Tokens (10)] (FixedStaticString64, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(100)", "-F", "char", "-H", "moodycamel [Batch With Tokens (100)] (char, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(100)", "-F", "int64_t", "-H", "moodycamel [Batch With Tokens (100)] (int64_t, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(100)", "-F", "FixedStaticString64", "-H", "moodycamel [Batch With Tokens (100)] (FixedStaticString64, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(1000)", "-F", "char", "-H", "moodycamel [Batch With Tokens (1000)] (char, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(1000)", "-F", "int64_t", "-H", "moodycamel [Batch With Tokens (1000)] (int64_t, size 65536)"],
#     [os.path.join(outdir, "Batch_Comps"), "-B", "-F", "QAC", "-F", "(1000)", "-F", "FixedStaticString64", "-H", "moodycamel [Batch With Tokens (1000)] (FixedStaticString64, size 65536)"],
# ]
#
# for argset in argsets:
#     cmds = [sys.executable, "run_multiple.py", os.path.join(indir, "FullMatrix")]
#     cmds.extend(argset)
#     print(f"[run_default.py] Running run_multiple.py {" ".join(f'"{cmd}"' if " " in cmd else cmd for cmd in cmds)}")
#     subprocess.run(cmds, stdout=sys.stdout, stderr=sys.stderr, shell=True, check=True)

argsets = [
    [os.path.join(outdir, "QAC_SingleComp", "Unbounded-sm", "Ticket Types"), "-S", "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-F", "16384", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
    [os.path.join(outdir, "QAC_SingleComp", "Unbounded-sm", "Blocking"), "-S", "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-F", "16384", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 16384, +n)"],
    [os.path.join(outdir, "QAC_SingleComp", "Unbounded-sm", "Feature Toggles"), "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-F", "16384", "-F", "Persistent Tickets|Batch (1)", "-f", "Blocking"],

    [os.path.join(outdir, "QAC_SingleComp", "Unbounded-lg", "Ticket Types"), "-S", "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-f", "16384", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
    [os.path.join(outdir, "QAC_SingleComp", "Unbounded-lg", "Blocking"), "-S", "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-f", "16384", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 10000000, +n)"],
    [os.path.join(outdir, "QAC_SingleComp", "Unbounded-lg", "Feature Toggles"), "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-f", "16384", "-F", "Persistent Tickets|Batch (1)", "-f", "Blocking"],

    [os.path.join(outdir, "QAC_SingleComp", "Bounded-sm", "Ticket Types"), "-S", "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-F", "131072", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
    [os.path.join(outdir, "QAC_SingleComp", "Bounded-sm", "Blocking"), "-S", "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-F", "131072", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 131072, +n)"],
    [os.path.join(outdir, "QAC_SingleComp", "Bounded-sm", "Feature Toggles"), "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-F", "131072", "-F", "Persistent Tickets|Batch (1)", "-f", "Blocking"],

    [os.path.join(outdir, "QAC_SingleComp", "Bounded-lg", "Ticket Types"), "-S", "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-f", "131072", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
    [os.path.join(outdir, "QAC_SingleComp", "Bounded-lg", "Blocking"), "-S", "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-f", "131072", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 10000000, +n)"],
    [os.path.join(outdir, "QAC_SingleComp", "Bounded-lg", "Feature Toggles"), "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-f", "131072", "-F", "Persistent Tickets|Batch (1)", "-f", "Blocking"],

    [os.path.join(outdir, "MoodyCamel_SingleComp", "Token Type"), "-S", "-c", "-F", "moodycamel", "--symmetrical-only", "-f", "Semaphore", "-f", "Blocking"],
    [os.path.join(outdir, "MoodyCamel_SingleComp", "Blocking"), "-S", "-c", "-F", "moodycamel", "--symmetrical-only", "-F", "With Tokens|Semaphore"],
]

for batchsize in ["(10)", "(100)", "(1000)"]:
    argsets.extend([
        [os.path.join(outdir, "QAC_SingleComp", "Unbounded-sm", "Ticket Types"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-F", "16384", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
        [os.path.join(outdir, "QAC_SingleComp", "Unbounded-sm", "Blocking"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-F", "16384", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 16384, +n)"],
        [os.path.join(outdir, "QAC_SingleComp", "Unbounded-sm", "Feature Toggles"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-F", "16384", "-F", "Persistent Tickets"],

        [os.path.join(outdir, "QAC_SingleComp", "Unbounded-lg", "Ticket Types"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-f", "16384", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
        [os.path.join(outdir, "QAC_SingleComp", "Unbounded-lg", "Blocking"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-f", "16384", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 25000000, +n)"],
        [os.path.join(outdir, "QAC_SingleComp", "Unbounded-lg", "Feature Toggles"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-f", "Bounded", "--symmetrical-only", "-f", "16384", "-F", "Persistent Tickets"],

        [os.path.join(outdir, "QAC_SingleComp", "Bounded-sm", "Ticket Types"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-F", "131072", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
        [os.path.join(outdir, "QAC_SingleComp", "Bounded-sm", "Blocking"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-F", "131072", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 131072, +n)"],
        [os.path.join(outdir, "QAC_SingleComp", "Bounded-sm", "Feature Toggles"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-F", "131072", "-F", "Persistent Tickets"],

        [os.path.join(outdir, "QAC_SingleComp", "Bounded-lg", "Ticket Types"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-f", "131072", "-F", "Persistent Tickets|Ephemeral Tickets|No Tickets", "-f", "+"],
        [os.path.join(outdir, "QAC_SingleComp", "Bounded-lg", "Blocking"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-f", "131072", "-F", "Persistent Tickets|Semaphore|Blocking", "-f", "+b", "-f", "[Persistent Tickets] (int64_t, size 25000000, +n)"],
        [os.path.join(outdir, "QAC_SingleComp", "Bounded-lg", "Feature Toggles"), "-B", "-F", batchsize, "-c", "-F", "QAC", "-F", "Bounded", "--symmetrical-only", "-f", "131072", "-F", "Persistent Tickets"],

        [os.path.join(outdir, "MoodyCamel_SingleComp", "Token Type"), "-B", "-F", batchsize, "-c", "-F", "moodycamel", "--symmetrical-only", "-f", "Semaphore", "-f", "Blocking"],
        [os.path.join(outdir, "MoodyCamel_SingleComp", "Blocking"), "-B", "-F", batchsize, "-c", "-F", "moodycamel", "--symmetrical-only", "-F", "With Tokens|Semaphore"],
    ])

for argset in argsets:
    cmds = [sys.executable, "run_multiple.py", os.path.join(indir, "SymmetricalComp")]
    cmds.extend(argset)
    print(f"[run_default.py] Running run_multiple.py {" ".join(f'"{cmd}"' if " " in cmd else cmd for cmd in cmds)}")
    subprocess.run(cmds, stdout=sys.stdout, stderr=sys.stderr, shell=True, check=True)
