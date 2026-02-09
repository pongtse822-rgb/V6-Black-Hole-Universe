import subprocess, sys, os, time

print("=== V6 Black Hole Membrane ===")
print("Running d.py...")

t = time.time()
r = subprocess.run(
    [sys.executable, "/content/drive/MyDrive/experiment/d.py"],
    stdout=open("output.txt", "w"),
    stderr=open("stderr.txt", "w"),
    timeout=600
)
elapsed = time.time() - t

print(f"Done in {elapsed:.0f}s (exit={r.returncode})")

if os.path.exists("stderr.txt"):
    with open("stderr.txt") as f:
        lines = f.readlines()
    print("\nLog (last 15 lines):")
    for line in lines[-15:]:
        print(f"  {line.rstrip()}")

if os.path.exists("RESULT.txt"):
    print(f"\nRESULT.txt: {os.path.getsize('RESULT.txt')} bytes")
    print("Open RESULT.txt for report!")
else:
    print("\nWARNING: RESULT.txt not found")
    print("Check stderr.txt for errors")

