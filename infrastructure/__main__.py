"""
Unified Pulumi Entry Point

This file routes to the appropriate stack implementation based on the stack name:
- Stack name containing 'base': infrastructure/base_stack.py (shared resources)
- All other stacks: infrastructure/environment_stack.py (dev, main, etc.)

This allows multiple stacks to share the same Pulumi.yaml while maintaining
separate codebases for base and environment infrastructure.
"""

import pulumi

# Get the current stack name
stack_name = pulumi.get_stack()
project_name = pulumi.get_project()

pulumi.log.info(f"🎯 Loading infrastructure for stack: {stack_name}")

# Route to appropriate stack implementation
if "base" in stack_name.lower():
    pulumi.log.info("📦 Loading base stack (shared infrastructure)")
    # Import and execute base stack code
    from infrastructure import base_stack
else:
    pulumi.log.info(f"🌍 Loading environment stack: {stack_name}")
    # Import and execute environment stack code
    from infrastructure import environment_stack
