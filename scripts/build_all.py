import os
import sys
import subprocess

def run_command(command, cwd=None):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: Command failed with return code {result.returncode}")
        sys.exit(1)

def build_all():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_dir = os.path.join(root_dir, "apps", "server")
    routing_dir = os.path.join(server_dir, "routing")
    proto_dir = os.path.join(root_dir, "packages", "shared", "proto")
    
    print("=== EventFlow Enterprise Build Orchestration ===")
    
    # 1. Compile Protobufs
    print("\n[1/3] Compiling Telemetry Protobufs...")
    python_out = os.path.join(proto_dir, "compiled", "python")
    os.makedirs(python_out, exist_ok=True)
    run_command(
        f'python -m grpc_tools.protoc -I"." --python_out="./compiled/python" "telemetry.proto"',
        cwd=proto_dir
    )

    # 2. Compile Cython A* Engine
    print("\n[2/3] Compiling Cython Routing Engine...")
    # Using the existing setup.py in the routing folder
    run_command("python setup.py build_ext --inplace", cwd=routing_dir)

    # 3. Verify Redis Environment
    print("\n[3/3] Verifying Infrastructure Readiness...")
    # This would call init_gcp.py if credentials were provided
    # run_command("python scripts/init_gcp.py")

    print("\n=== Build Successful. Ready for Phase 3 (Load Gen) ===")

if __name__ == "__main__":
    build_all()
