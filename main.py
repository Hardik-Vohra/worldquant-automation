import subprocess

print("Submitting Alpha...")
subprocess.run(["python", "submit_alpha.py"])

print("Polling Simulation...")
subprocess.run(["python", "poll_sim.py"])

print("Collecting Results...")
subprocess.run(["python", "collector.py"])

print("Done.")